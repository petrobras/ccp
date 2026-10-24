"""Trends, change points and time to threshold of evaluation KPIs.

The KPI series of an :class:`ccp.Evaluation` are reduced to one robust value
per period (the median of the valid rows), which removes most of the noise and
the autocorrelation of plant data. On that series:

- change points are found with PELT (Killick, Fearnhead and Eckley 2012,
  doi 10.1080/01621459.2012.737745) on a piecewise-linear model (a level and
  a slope per segment), since degradation is a ramp and a wash a step; the
  noise scale is estimated from the median absolute first difference, which
  neither a step nor a slope inflates;
- the trend of the last segment (since the last change point) is the
  Theil-Sen slope with its 95 % interval (Sen 1968), which ignores outliers;
- the time to a threshold extrapolates that line, with the interval from the
  slope limits.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .. import Q_

__all__ = [
    "KPI_INFO",
    "KpiTrend",
    "TrendReport",
    "analyse_trends",
    "change_points",
    "evaluation_rows",
    "robust_sigma",
    "theil_sen",
]

# label, unit and whether a higher value is better (None: neither)
KPI_INFO = {
    "delta_eff": ("Efficiency deviation", "points", True),
    "delta_head": ("Head deviation", "%", True),
    "delta_power": ("Power deviation", "%", False),
    "delta_p_disch": ("Discharge pressure deviation", "%", True),
    "flow_dev": ("Flow capacity deviation", "%", True),
    "delta_Td": ("Discharge temperature deviation", "K", False),
    "health_index": ("Health index", "-", True),
    "delta_power_balance": ("Power balance residual", "%", None),
}

DEFAULT_KPIS = (
    "delta_eff",
    "delta_head",
    "flow_dev",
    "delta_Td",
    "delta_power_balance",
)

# thresholds for the time to threshold, in KPI units
DEFAULT_THRESHOLDS = {"delta_eff": -2.0, "delta_head": -2.0, "flow_dev": -3.0}

HOURS = 1000.0  # slopes are reported per 1000 h


def evaluation_rows(df):
    """Rows of an evaluation result where the points were calculated."""
    mask = df["delta_eff"] != -1
    if "valid" in df.columns:
        mask &= df["valid"].astype(bool)
    return df[mask]


def robust_sigma(y):
    """Noise standard deviation of a series that may contain steps.

    Median absolute first difference / (0.6745 sqrt 2): a step changes one
    difference only. When most differences are zero (a quantised or
    deadband-compressed series) that is 0, and the noise is taken as the
    quantisation error of the typical non-zero difference ``q``,
    ``q / sqrt(12)``; 0 for a constant series.
    """
    y = np.asarray(y, dtype=float)
    if len(y) < 3:
        return float(np.std(y)) if len(y) > 1 else 0.0
    d = np.diff(y)
    mad = np.median(np.abs(d - np.median(d)))
    if mad > 0:
        return float(mad / (0.6745 * np.sqrt(2)))
    jumps = np.abs(d[d != 0])
    if len(jumps) == 0:
        return 0.0
    return float(np.median(jumps) / np.sqrt(12))


def change_points(y, penalty=None, min_size=3, sigma=None, t=None):
    """Change points of a piecewise-linear series by PELT.

    Each segment is a straight line; a change point is a step of the level
    and/or of the slope.

    Parameters
    ----------
    y : array_like
        Series values (no NaN).
    penalty : float, optional
        Cost of one change, in units of the normalised squared error. The
        default is ``4 ln(n)`` (a modified BIC for two parameters per
        segment, conservative for the autocorrelated residuals of plant
        data).
    min_size : int, optional
        Minimum number of values in a segment. The default is 3.
    sigma : float, optional
        Noise standard deviation. The default is :func:`robust_sigma`.
    t : array_like, optional
        Times of the values. The default is equally spaced.

    Returns
    -------
    list of int
        Indices where a new segment starts (empty when there is no change).
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < 2 * min_size:
        return []
    t = np.arange(n, dtype=float) if t is None else np.asarray(t, dtype=float)
    t = (t - t[0]) / max(np.ptp(t), 1e-12)
    if sigma is None:
        sigma = robust_sigma(y)
    if not sigma > 0:
        sigma = float(np.std(y)) or 1.0
    z = y / sigma
    if penalty is None:
        penalty = 4 * np.log(n)

    def cumulative(x):
        return np.concatenate([[0.0], np.cumsum(x)])

    st, stt, sz, szz, stz = (
        cumulative(t),
        cumulative(t * t),
        cumulative(z),
        cumulative(z * z),
        cumulative(t * z),
    )

    def cost(start, end):
        # squared error of the least-squares line through z[start:end]
        # (vectorised in start)
        m = end - start
        s_t = st[end] - st[start]
        s_tt = stt[end] - stt[start]
        s_z = sz[end] - sz[start]
        s_zz = szz[end] - szz[start]
        s_tz = stz[end] - stz[start]
        var_t = s_tt - s_t**2 / m
        cov = s_tz - s_t * s_z / m
        with np.errstate(divide="ignore", invalid="ignore"):
            explained = np.where(var_t > 1e-300, cov**2 / var_t, 0.0)
        return np.maximum(s_zz - s_z**2 / m - explained, 0.0)

    best = np.full(n + 1, np.inf)
    best[0] = -penalty
    last = np.zeros(n + 1, dtype=int)
    candidates = np.array([0])
    for end in range(min_size, n + 1):
        ready = candidates[end - candidates >= min_size]
        waiting = candidates[end - candidates < min_size]
        values = best[ready] + cost(ready, end)
        k = int(np.argmin(values))
        best[end] = values[k] + penalty
        last[end] = ready[k]
        # pruning: a start that cannot beat the best now never will
        candidates = np.concatenate([ready[values <= best[end]], waiting, [end]])
    changes = []
    end = n
    while end > 0:
        start = last[end]
        if start > 0:
            changes.append(int(start))
        end = start
    return sorted(changes)


def theil_sen(t, y, alpha=0.95):
    """Theil-Sen slope and intercept of ``y(t)`` with the slope interval.

    Returns
    -------
    tuple
        ``(slope, intercept, slope_low, slope_high)``; NaN with fewer than
        three values.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(t) < 3 or np.ptp(t) == 0:
        return (np.nan,) * 4
    result = stats.theilslopes(y, t, alpha=alpha)
    return (
        float(result.slope),
        float(result.intercept),
        float(result.low_slope),
        float(result.high_slope),
    )


@dataclass
class KpiTrend:
    """Trend analysis of one KPI.

    Times are hours from the first period. Slopes are in KPI units per 1000 h.
    """

    kpi: str
    label: str
    unit: str
    higher_is_better: object
    series: pd.Series
    counts: pd.Series
    sigma: float
    change_points: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    slope: float = np.nan
    slope_low: float = np.nan
    slope_high: float = np.nan
    intercept: float = np.nan
    current: float = np.nan
    threshold: float = None
    time_to_threshold: float = np.nan
    time_to_threshold_low: float = np.nan
    time_to_threshold_high: float = np.nan
    baseline: dict = None

    @property
    def last_change(self):
        return self.change_points[-1] if self.change_points else None

    def fitted(self):
        """Line of the last segment as a series over its periods."""
        if not self.segments or not np.isfinite(self.slope):
            return pd.Series(dtype=float)
        start = self.segments[-1]["start"]
        index = self.series.index[self.series.index >= start]
        t = _hours(index, self.series.index[0])
        return pd.Series(self.intercept + self.slope / HOURS * t, index=index)

    def to_dict(self):
        def num(x):
            return None if x is None or not np.isfinite(x) else float(x)

        return {
            "kpi": self.kpi,
            "label": self.label,
            "unit": self.unit,
            "higher_is_better": self.higher_is_better,
            "time": [t.isoformat() for t in self.series.index],
            "values": [num(v) for v in self.series.to_numpy()],
            "counts": [int(c) for c in self.counts.to_numpy()],
            "sigma": num(self.sigma),
            "change_points": [
                {**c, "time": c["time"].isoformat(), "shift": num(c["shift"])}
                for c in self.change_points
            ],
            "segments": [
                {
                    "start": s["start"].isoformat(),
                    "end": s["end"].isoformat(),
                    "mean": num(s["mean"]),
                    "slope": num(s["slope"]),
                    "first": num(s["first"]),
                    "last": num(s["last"]),
                }
                for s in self.segments
            ],
            "slope": num(self.slope),
            "slope_low": num(self.slope_low),
            "slope_high": num(self.slope_high),
            "current": num(self.current),
            "threshold": num(self.threshold),
            "time_to_threshold": num(self.time_to_threshold),
            "time_to_threshold_low": num(self.time_to_threshold_low),
            "time_to_threshold_high": num(self.time_to_threshold_high),
            "fitted": {
                "time": [t.isoformat() for t in self.fitted().index],
                "values": [num(v) for v in self.fitted().to_numpy()],
            },
        }


@dataclass
class TrendReport:
    """Trend analyses of the KPIs of an evaluation."""

    trends: dict
    freq: str

    def __getitem__(self, kpi):
        return self.trends[kpi]

    def __iter__(self):
        return iter(self.trends.values())

    def to_frame(self):
        """One row per KPI: current value, slope, change points, time to threshold."""
        rows = []
        for t in self:
            rows.append(
                {
                    "kpi": t.kpi,
                    "label": t.label,
                    "unit": t.unit,
                    "current": t.current,
                    "slope_per_1000h": t.slope,
                    "slope_low": t.slope_low,
                    "slope_high": t.slope_high,
                    "change_points": len(t.change_points),
                    "last_change": t.last_change["time"] if t.last_change else None,
                    "threshold": t.threshold,
                    "time_to_threshold_h": t.time_to_threshold,
                    "time_to_threshold_low_h": t.time_to_threshold_low,
                    "time_to_threshold_high_h": t.time_to_threshold_high,
                }
            )
        return pd.DataFrame(rows).set_index("kpi")

    def to_dict(self):
        return {
            "freq": self.freq,
            "trends": {k: t.to_dict() for k, t in self.trends.items()},
        }

    def plot(self, kpi, fig=None):
        """Plotly figure of a KPI: period medians, segments, trend, change points."""
        import plotly.graph_objects as go

        t = self.trends[kpi]
        fig = fig or go.Figure()
        fig.add_trace(
            go.Scatter(
                x=t.series.index,
                y=t.series.to_numpy(),
                mode="markers",
                name=f"{self.freq} median",
                marker=dict(size=5, opacity=0.7),
            )
        )
        for s in t.segments:
            fig.add_trace(
                go.Scatter(
                    x=[s["start"], s["end"]],
                    y=[s["first"], s["last"]],
                    mode="lines",
                    line=dict(width=1, dash="dot"),
                    name="segment",
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        fitted = t.fitted()
        if not fitted.empty:
            fig.add_trace(
                go.Scatter(
                    x=fitted.index,
                    y=fitted.to_numpy(),
                    mode="lines",
                    name=f"trend {t.slope:+.2f} {t.unit}/1000 h",
                    line=dict(width=2),
                )
            )
        for c in t.change_points:
            fig.add_vline(x=c["time"], line_width=1, line_dash="dash", opacity=0.5)
        if t.threshold is not None:
            fig.add_hline(y=t.threshold, line_width=1, line_dash="dot", opacity=0.6)
        fig.update_layout(
            xaxis_title="Time", yaxis_title=f"{t.label} ({t.unit})", showlegend=True
        )
        return fig


def _hours(index, origin):
    seconds = (index - origin).total_seconds().to_numpy()
    return Q_(seconds, "s").to("h").m


def _baseline_correct(df, kpi, baseline_days):
    """Subtract, per cluster, the median of the cluster's first ``baseline_days``."""
    values = df[kpi].astype(float).copy()
    baselines = {}
    if "cluster" not in df.columns:
        groups = [(0, df.index)]
    else:
        groups = [(c, g.index) for c, g in df.groupby("cluster")]
    for cluster, index in groups:
        rows = values.loc[index].dropna()
        if rows.empty:
            continue
        window = rows[rows.index < rows.index[0] + pd.Timedelta(days=baseline_days)]
        baselines[int(cluster)] = float(window.median())
        values.loc[index] = values.loc[index] - baselines[int(cluster)]
    return values, baselines


def _analyse_kpi(values, kpi, freq, penalty, min_size, threshold, min_count):
    label, unit, higher = KPI_INFO.get(kpi, (kpi, "", None))
    grouped = values.dropna().resample(freq)
    series = grouped.median()
    counts = grouped.count()
    keep = counts >= min_count
    series, counts = series[keep], counts[keep]
    sigma = robust_sigma(series.to_numpy())
    trend = KpiTrend(
        kpi=kpi,
        label=label,
        unit=unit,
        higher_is_better=higher,
        series=series,
        counts=counts,
        sigma=sigma,
        threshold=threshold,
    )
    if series.empty:
        return trend
    y = series.to_numpy()
    t = _hours(series.index, series.index[0])
    starts = [0] + change_points(
        y, penalty=penalty, min_size=min_size, sigma=sigma, t=t
    )
    bounds = starts + [len(y)]
    lines = []
    for i, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        if b - a >= 2 and np.ptp(t[a:b]) > 0:
            slope, intercept = np.polyfit(t[a:b], y[a:b], 1)
        else:
            slope, intercept = 0.0, float(np.mean(y[a:b]))
        lines.append((slope, intercept))
        trend.segments.append(
            {
                "start": series.index[a],
                "end": series.index[b - 1],
                "mean": float(np.mean(y[a:b])),
                "slope": float(slope * HOURS),
                "first": float(intercept + slope * t[a]),
                "last": float(intercept + slope * t[b - 1]),
            }
        )
        if i > 0:
            # step at the change: the new line minus the previous line
            # extrapolated to the first period of the new segment
            previous = lines[i - 1]
            shift = (intercept + slope * t[a]) - (previous[1] + previous[0] * t[a])
            if higher is None:
                kind = "shift"
            else:
                kind = "recovery" if (shift > 0) == bool(higher) else "drop"
            trend.change_points.append(
                {"time": series.index[a], "shift": float(shift), "kind": kind}
            )
    # trend of the last segment
    last = series.index >= trend.segments[-1]["start"]
    slope, intercept, lo, hi = theil_sen(t[last], y[last])
    trend.slope, trend.slope_low, trend.slope_high = (
        slope * HOURS,
        lo * HOURS,
        hi * HOURS,
    )
    trend.intercept = intercept
    if np.isfinite(slope):
        trend.current = float(intercept + slope * t[-1])
    else:
        trend.current = float(np.median(y[last]))
    if threshold is not None and np.isfinite(slope):
        times = [_time_to(threshold, trend.current, s, higher) for s in (slope, lo, hi)]
        trend.time_to_threshold = times[0]
        # the steeper limit reaches the threshold first
        trend.time_to_threshold_low = min(times[1:])
        trend.time_to_threshold_high = max(times[1:])
    return trend


def _time_to(threshold, current, slope, higher_is_better=None):
    """Hours until a line through ``current`` with ``slope`` reaches ``threshold``.

    ``slope`` is per hour; inf when the line moves away from the threshold.
    0 when ``current`` is already on the bad side of the threshold: below it
    when a higher value is better, above it when a lower value is better
    and, for a KPI without a direction, beyond it as seen from 0 (the
    as-new deviation).
    """
    if higher_is_better is None and threshold != 0:
        higher_is_better = threshold < 0
    if higher_is_better is not None:
        if (current <= threshold) if higher_is_better else (current >= threshold):
            return 0.0
    gap = threshold - current
    if gap == 0:
        return 0.0
    if slope == 0 or not np.isfinite(slope) or np.sign(slope) != np.sign(gap):
        return np.inf
    return float(gap / slope)


def analyse_trends(
    df,
    kpis=None,
    freq="1D",
    penalty=None,
    min_size=3,
    thresholds=None,
    baseline_days=None,
    min_count=1,
):
    """Trends, change points and time to threshold of evaluation KPIs.

    Parameters
    ----------
    df : pandas.DataFrame
        Evaluation results (``Evaluation.df``) with a DatetimeIndex.
    kpis : sequence of str, optional
        KPI columns. The default is the KPIs of ``DEFAULT_KPIS`` present in
        ``df`` with at least one value.
    freq : str, optional
        Period of the medians (pandas offset alias). The default is "1D".
    penalty : float, optional
        PELT penalty per change point (see :func:`change_points`).
    min_size : int, optional
        Minimum number of periods in a segment. The default is 3.
    thresholds : dict, optional
        Threshold per KPI for the time to threshold, in KPI units (of the
        baseline-corrected KPI when ``baseline_days`` is given). Merged with
        ``DEFAULT_THRESHOLDS``; set a KPI to None to skip it.
    baseline_days : float, optional
        When given, each KPI is taken relative to the median of the first
        ``baseline_days`` of each cluster, which removes the error of the
        converted curve in each operating region.
    min_count : int, optional
        Minimum number of valid rows in a period. The default is 1.

    Returns
    -------
    TrendReport
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Trend analysis needs a DatetimeIndex.")
    rows = evaluation_rows(df)
    if kpis is None:
        kpis = [k for k in DEFAULT_KPIS if k in rows.columns and rows[k].notna().any()]
    limits = dict(DEFAULT_THRESHOLDS)
    limits.update(thresholds or {})
    trends = {}
    for kpi in kpis:
        if kpi not in rows.columns:
            raise KeyError(f"KPI column {kpi!r} not found in the evaluation results.")
        values = rows[kpi].astype(float)
        baselines = None
        if baseline_days is not None:
            values, baselines = _baseline_correct(rows, kpi, baseline_days)
        trend = _analyse_kpi(
            values, kpi, freq, penalty, min_size, limits.get(kpi), min_count
        )
        trend.baseline = baselines
        trends[kpi] = trend
    return TrendReport(trends=trends, freq=freq)
