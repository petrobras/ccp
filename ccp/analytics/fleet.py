"""Hierarchical Bayesian model of a fleet of compressors of one design.

Compressors built to one design differ only by manufacturing tolerances,
installation, instruments and degradation. This module pools the shop tests
and the field data of every unit of such a fleet in one model, so that each
unit is judged against what is normal for its design: a unit with little data
borrows strength from its siblings, and a deviation shared by the whole fleet
(an optimistic vendor curve, an equation-of-state bias) is not mistaken for a
problem of one unit.

Observations
------------
For each valid evaluation row the model uses the head and efficiency
residuals against the expected (converted) curve,

    r_head = ln(head / expected_head),   r_eff = eff - expected_eff,

the log-slopes of the expected curve (``head_slope``, ``eff_slope``), and,
when the driver power is known, the power-balance residual
``r_power = ln(power_coupling / power_shaft)``. A shop test gives the same
residuals against the design curve converted to the shop suction.

Model (first order in deviations of a few percent)
--------------------------------------------------
Unit as-built deviation from the vendor curve, for flow capacity, head and
efficiency (k)::

    theta[u, k] = mu[k] + tau_unit[k] z[u, k]

Field level of head and efficiency (f)::

    level[u, f](t) = theta[u, f] + site[s(u), f] + install[u, f] + health[u, f](t)
                     + period[u, f](t)
    health[u, f](t) = health[u, f](t - dt) + rate[u, f] dt + sigma_walk[f] sqrt(dt) e
    e ~ StudentT(3),  rate[u, f] = mu_rate[f] + tau_rate[f] z

Residuals::

    r_head = level_head - (theta_flow + bias_flow) head_slope
             + k_head_T bias_T + k_head_p bias_pr + e
    r_eff = level_eff - (theta_flow + bias_flow) eff_slope
            + k_eff_T bias_T + k_eff_p bias_pr + e
    r_power = bias_driver - w (bias_flow + bias_T / (Td - Ts)) + e
    shop: r_head = theta_head - theta_flow head_slope + e_shop
          r_eff = theta_eff - theta_flow eff_slope + e_shop

``bias_T`` is a bias of the measured temperature rise (K), ``bias_pr`` a
relative bias of the measured pressure ratio, ``bias_flow`` of the flow meter
and ``bias_driver`` of the driver power; their sensitivities ``k`` are the
ideal-gas ones evaluated at each row. Without driver power a flow-meter bias
and a flow-capacity deviation have the same signature and only their sum is
learned. A Student-t random walk follows washes and sudden losses without
discrete change points; ``health`` is zero on average over each unit's
first 14 days of data. ``period`` is a transient disturbance of one period
(normal, not carried over), so that a disturbed day is not read as two
opposite steps of the health. The row errors are Student-t with a scale per
unit plus a model-error floor (the first-order and ideal-gas
approximations), and rows on the steep part of the curve near choke
(``max_head_slope``) are left out, where the first-order model fails.

The model is fitted by NUTS with PyMC (``pip install ccp-performance[bayes]``);
nutpie is used when installed. Priors follow the scatter reported for identical
units (about 2 % head and 1.5 % efficiency, Tavares et al. 2013) and the
advice of Gelman (2006) to use informative scale priors with few groups; see
:class:`FleetPriors`.
"""

import io
import json
import warnings
import zipfile
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .. import Q_
from .trends import evaluation_rows

__all__ = [
    "Fleet",
    "FleetPriors",
    "FleetUnit",
    "field_observations",
    "pymc_available",
    "shop_observations",
    "unit_shop_observations",
    "simulate_fleet",
]

HOURS = 1000.0  # rates are reported per 1000 h


def _hours(timedelta):
    """Length of a pandas Timedelta (or offset alias) in hours."""
    return Q_(pd.Timedelta(timedelta).total_seconds(), "s").to("h").m


def _days(timedelta):
    """Length of a pandas Timedelta (or offset alias) in days."""
    return Q_(pd.Timedelta(timedelta).total_seconds(), "s").to("day").m


COMPONENTS = ["flow", "head", "eff"]
FIELDS = ["head", "eff"]
RESIDUALS = ["head", "eff", "power"]
# unit of the sampled health levels (0.1 %)
HEALTH_UNIT = 0.001
# the health is zero on average over each unit's first ANCHOR_DAYS of data
ANCHOR_DAYS = 14
# finest first: the first period giving at most max_bins periods is used
FREQS = ["1D", "2D", "7D", "14D", "30D", "91D"]


def pymc_available():
    """True when PyMC can be imported."""
    try:
        import pymc  # noqa: F401
    except ImportError:
        return False
    return True


def _require_pymc():
    try:
        import pymc
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError(
            "The fleet model needs PyMC. Install it with "
            "`pip install ccp-performance[bayes]`."
        ) from exc
    return pymc


@dataclass
class FleetPriors:
    """Prior scales of the fleet model.

    Deviations are fractions (0.01 = 1 % head or 1 efficiency point), rates
    are per 1000 h, the random-walk scale is per square root of a day and
    ``bias_T`` is in kelvin.
    """

    # design level: fleet mean deviation from the vendor curve
    mu_flow: float = 0.05
    mu_head: float = 0.05
    mu_eff: float = 0.05
    # manufacturing scatter between units (half-normal scales)
    tau_unit_flow: float = 0.02
    tau_unit_head: float = 0.02
    tau_unit_eff: float = 0.015
    # site scatter (half-normal scales) and installation scatter (mean of a
    # Gamma prior with shape 2)
    tau_site_head: float = 0.02
    tau_site_eff: float = 0.02
    tau_install_head: float = 0.03
    tau_install_eff: float = 0.03
    # degradation rate: fleet mean and scatter, per 1000 h
    mu_rate_head: float = 0.005
    mu_rate_eff: float = 0.005
    tau_rate_head: float = 0.005
    tau_rate_eff: float = 0.005
    # random walk of the health (per sqrt(day), mean of a Gamma prior with
    # shape 4) and its tail
    sigma_walk_head: float = 0.002
    sigma_walk_eff: float = 0.002
    walk_nu: float = 3.0
    # transient disturbance of one period (half-normal scales)
    sigma_period_head: float = 0.003
    sigma_period_eff: float = 0.003
    # row noise (half-normal scales) and its tail
    noise_head: float = 0.02
    noise_eff: float = 0.02
    noise_power: float = 0.02
    noise_nu: float = 4.0
    # error of the model itself (first order in the curve shift, ideal-gas
    # bias sensitivities, equation of state), added in quadrature to the row
    # noise: with very precise data it keeps the posterior from collapsing
    # onto a ridge the approximations cannot resolve
    model_error_head: float = 0.002
    model_error_eff: float = 0.002
    model_error_power: float = 0.002
    # shop test standard deviations
    shop_head: float = 0.005
    shop_eff: float = 0.005
    # instruments: temperature-rise bias (K), pressure-ratio, flow, driver power
    bias_T: float = 0.42
    bias_pr: float = 0.0035
    bias_flow: float = 0.01
    bias_driver: float = 0.02


@dataclass
class FleetUnit:
    """One compressor of a fleet.

    Parameters
    ----------
    name : str
        Unit name (e.g. the tag or the serial number).
    evaluation : ccp.Evaluation, optional
        Field evaluation of the unit (its ``df`` must have the analytics
        columns, i.e. be calculated with this ccp version).
    site : str, optional
        Site of the unit. Units at one site share a site effect.
    shop : ccp.StraightThrough or list of ccp.Point, optional
        Shop test at specified conditions (``StraightThrough.points_flange_sp``
        or the points themselves).
    design : ccp.Impeller, optional
        Design curve to compare the shop test with. The default converts the
        evaluation's design impellers to the shop suction.
    """

    name: str
    evaluation: object = None
    site: str = None
    shop: object = None
    design: object = None


def _sensitivities(eff, ps, Ts, pd_, Td):
    """Ideal-gas sensitivities of the residuals to instrument biases.

    With ``eff = (R/cp) ln(pd/ps) / ln(Td/Ts)`` and
    ``head = R ln(pd/ps) (Td - Ts) / ln(Td/Ts)``:

    - per kelvin of discharge-temperature bias: ``k_eff_T``, ``k_head_T``
      (``d ln head``) and ``k_power_T`` (``d ln gas power``);
    - per relative bias of the pressure ratio: ``k_eff_p``, ``k_head_p``.
    """
    log_t = np.log(Td / Ts)
    log_p = np.log(pd_ / ps)
    rise = Td - Ts
    return {
        "k_eff_T": -eff / (Td * log_t),
        "k_head_T": 1 / rise - 1 / (Td * log_t),
        "k_power_T": 1 / rise,
        "k_eff_p": eff / log_p,
        "k_head_p": 1 / log_p,
    }


def field_observations(evaluation):
    """Fleet-model observations of an evaluation (one row per valid point).

    Returns
    -------
    pandas.DataFrame
        Indexed by time, with ``r_head``, ``r_eff``, ``head_slope``,
        ``eff_slope``, the instrument sensitivities and, when the driver
        power is known, ``r_power`` and ``w`` (gas power over shaft power).
    """
    df = evaluation_rows(evaluation.df)
    needed = ["head_slope", "eff_slope", "expected_head", "expected_eff"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(
            f"The evaluation results have no {missing} columns: recalculate the "
            "points with this ccp version (Evaluation.calculate_points())."
        )
    units = evaluation.data_units or {}

    def si(column, unit):
        return Q_(df[column].to_numpy(dtype=float), units.get(column, unit)).to(unit).m

    ps, pd_ = si("ps", "Pa"), si("pd", "Pa")
    Ts, Td = si("Ts", "K"), si("Td", "K")
    eff = df["eff"].to_numpy(dtype=float)
    obs = pd.DataFrame(
        {
            "r_head": np.log(df["head"] / df["expected_head"]).to_numpy(),
            "r_eff": (df["eff"] - df["expected_eff"]).to_numpy(),
            "head_slope": df["head_slope"].to_numpy(),
            "eff_slope": df["eff_slope"].to_numpy(),
            **_sensitivities(eff, ps, Ts, pd_, Td),
        },
        index=df.index,
    )
    if "power_coupling" in df.columns:
        with np.errstate(divide="ignore", invalid="ignore"):
            r_power = np.log(df["power_coupling"] / df["power_shaft"]).to_numpy()
        w = (df["power"] / df["power_shaft"]).to_numpy()
        # a driver power of 0 or below (a dead transmitter) is a missing value
        bad = ~(np.isfinite(r_power) & np.isfinite(w))
        obs["r_power"] = np.where(bad, np.nan, r_power)
        obs["w"] = np.where(bad, np.nan, w)
    ok = (Td > Ts) & (pd_ > ps) & np.isfinite(obs[["r_head", "r_eff"]]).all(axis=1)
    ok &= np.isfinite(obs[["head_slope", "eff_slope"]]).all(axis=1)
    return obs[ok.to_numpy()]


def shop_observations(points, design):
    """Shop-test residuals of ``points`` against the ``design`` impeller."""
    from ..evaluation import _curve_slopes

    rows = []
    for p in points:
        expected = design.point(flow_v=p.flow_v, speed=p.speed)
        curve = design._curve_data(expected.speed)
        head_slope, eff_slope = _curve_slopes(curve, p.flow_v.m, expected.head.m)
        rows.append(
            {
                "r_head": float(np.log(p.head.m / expected.head.m)),
                "r_eff": float(p.eff.m - expected.eff.m),
                "head_slope": head_slope,
                "eff_slope": eff_slope,
            }
        )
    obs = pd.DataFrame(rows)
    return obs[np.isfinite(obs).all(axis=1)]


def unit_shop_observations(unit):
    """Shop-test observations of a :class:`FleetUnit` (None without a shop test)."""
    if unit.shop is None:
        return None
    points = getattr(unit.shop, "points_flange_sp", unit.shop)
    points = list(points)
    if not points:
        return None
    design = unit.design
    if design is None:
        from ..impeller import Impeller

        if unit.evaluation is None:
            raise ValueError(
                f"Unit {unit.name!r}: give the design impeller to compare the "
                "shop test with."
            )
        design = Impeller.convert_from(
            unit.evaluation.impellers, suc=points[0].suc, speed="same"
        )
    return shop_observations(points, design)


def _posterior_dataset(idata):
    """Posterior group as an xarray Dataset (InferenceData or DataTree)."""
    group = idata["posterior"]
    return group.to_dataset() if hasattr(group, "to_dataset") else group


def _sample_stat(idata, name):
    try:
        group = idata["sample_stats"]
    except (KeyError, AttributeError):
        return None
    group = group.to_dataset() if hasattr(group, "to_dataset") else group
    return group[name].values if name in group else None


# default limit of |d ln head / d ln flow| of the rows used (see Fleet)
MAX_HEAD_SLOPE = 1.5
# convergence limit of the rank-normalised R-hat (Vehtari et al. 2021)
MAX_RHAT = 1.01
# variables checked by Fleet.diagnostics
DIAGNOSTIC_VARIABLES = [
    "mu",
    "tau_unit",
    "theta",
    "tau_install",
    "field_offset",
    "mu_rate",
    "tau_rate",
    "rate",
    "sigma_walk",
    "sigma_period",
    "health",
    "bias_T",
    "bias_pr",
    "bias_flow",
    "bias_driver",
    "tau_site",
    "sigma",
]


def _split_chains(x):
    """Draws ``x`` (chain, draw) with each chain cut in two halves."""
    half = x.shape[1] // 2
    return np.concatenate([x[:, :half], x[:, -half:]], axis=0)


def _z_scale(x):
    """Rank-normalised draws: normal scores of the ranks over all chains."""
    from scipy import stats

    ranks = stats.rankdata(x, method="average").reshape(x.shape)
    return stats.norm.ppf((ranks - 0.375) / (x.size + 0.25))


def _rhat(x):
    """Potential scale reduction of chains ``x`` (chain, draw)."""
    draws = x.shape[1]
    within = x.var(axis=1, ddof=1).mean()
    between = draws * x.mean(axis=1).var(ddof=1)
    var = (draws - 1) / draws * within + between / draws
    return float(np.sqrt(var / within))


def _split_rhat(x):
    """Rank-normalised split R-hat of draws ``x`` (chain, draw).

    The larger of the bulk R-hat (on the rank-normalised draws) and the
    tail R-hat (on the rank-normalised distances to the median), as in
    Vehtari et al., Rank-normalization, folding and localization: an
    improved R-hat for assessing convergence of MCMC, Bayesian Analysis 16
    (2021), doi 10.1214/20-BA1221; to be compared with 1.01. NaN for fewer
    than four draws per chain or constant draws.
    """
    if x.shape[1] < 4 or np.ptp(x) == 0:
        return np.nan
    split = _split_chains(x)
    bulk = _rhat(_z_scale(split))
    tail = _rhat(_z_scale(np.abs(split - np.median(split))))
    return max(bulk, tail)


def _ess(x):
    """Bulk effective sample size of draws ``x`` (chain, draw).

    Of the rank-normalised split chains (Vehtari et al. 2021, see
    :func:`_split_rhat`), with the autocorrelations combined over chains as
    in Gelman et al., Bayesian Data Analysis (3rd ed., section 11.5) and
    truncated by Geyer's initial monotone sequence.
    """
    if x.shape[1] < 8 or np.ptp(x) == 0:
        return np.nan
    x = _z_scale(_split_chains(x))
    chains, draws = x.shape
    centered = x - x.mean(axis=1, keepdims=True)
    size = 2 ** int(np.ceil(np.log2(2 * draws)))
    spectrum = np.fft.rfft(centered, n=size, axis=1)
    acov = np.fft.irfft(spectrum * np.conj(spectrum), n=size, axis=1)[:, :draws] / draws
    within = x.var(axis=1, ddof=1).mean()
    between = x.mean(axis=1).var(ddof=1)
    var_plus = (draws - 1) / draws * within + between
    rho = 1 - (within - acov.mean(axis=0)) / var_plus
    rho[0] = 1.0
    total = 0.0
    previous = np.inf
    for t in range(0, draws - 1, 2):
        pair = rho[t] + rho[t + 1]
        if pair < 0:
            break
        # initial monotone sequence
        pair = min(pair, previous)
        previous = pair
        total += pair
    tau = max(-1 + 2 * total, 1 / np.log10(chains * draws))
    return float(chains * draws / tau)


class Fleet:
    """Hierarchical Bayesian model of compressors of one design.

    Parameters
    ----------
    units : list of FleetUnit
        Units of the fleet (at least two).
    priors : FleetPriors, optional
        Prior scales. The default is ``FleetPriors()``.
    freq : str, optional
        Period of the health random walk (pandas offset alias). The default
        picks the finest of 1, 2, 7, 14, 30 or 91 days giving at most
        ``max_bins`` periods (weekly for about two years of data).
    rows_per_bin : int, optional
        Maximum number of rows per unit and period (evenly spaced), which
        limits the weight of autocorrelated plant data. The default is 12.
    max_bins : int, optional
        Maximum number of periods for the automatic ``freq``. The default
        is 120.
    max_head_slope : float, optional
        Rows where the expected head curve is steeper than this
        (``|d ln head / d ln flow|``) are left out. Near choke a flow shift
        of 1 or 2 % changes the head far from linearly, and a flow-meter
        error dominates the residual. The default is 1.5.

    Examples
    --------
    >>> from ccp.analytics.fleet import Fleet, simulate_fleet
    >>> field, shop, truth = simulate_fleet(n_units=3, days=60, seed=1)
    >>> fleet = Fleet.from_observations(field, shop)
    >>> fleet.fit(draws=300, tune=300, chains=2, random_seed=1)  # doctest: +SKIP
    >>> fleet.summary()  # doctest: +SKIP
    """

    def __init__(
        self,
        units,
        priors=None,
        freq=None,
        rows_per_bin=12,
        max_bins=120,
        max_head_slope=MAX_HEAD_SLOPE,
    ):
        units = list(units)
        names = [u.name for u in units]
        if len(set(names)) != len(names):
            raise ValueError("Fleet units need distinct names.")
        field_rows = []
        shop_rows = []
        for unit in units:
            if unit.evaluation is not None:
                obs = field_observations(unit.evaluation)
                obs = obs.assign(unit=unit.name, site=unit.site or "site")
                field_rows.append(obs)
            shop = unit_shop_observations(unit)
            if shop is not None:
                shop_rows.append(shop.assign(unit=unit.name))
        field = pd.concat(field_rows) if field_rows else pd.DataFrame()
        shop = pd.concat(shop_rows, ignore_index=True) if shop_rows else None
        sites = {u.name: (u.site or "site") for u in units}
        self._setup(
            field,
            shop,
            names,
            sites,
            priors,
            freq,
            rows_per_bin,
            max_bins,
            max_head_slope,
        )

    @classmethod
    def from_observations(
        cls,
        field,
        shop=None,
        sites=None,
        priors=None,
        freq=None,
        rows_per_bin=12,
        max_bins=120,
        max_head_slope=MAX_HEAD_SLOPE,
        units=None,
    ):
        """Fleet from observation tables (see :func:`field_observations`).

        Parameters
        ----------
        field : pandas.DataFrame
            Field observations of all units, indexed by time, with ``unit``
            and ``site`` columns.
        shop : pandas.DataFrame, optional
            Shop observations with a ``unit`` column.
        sites : dict, optional
            Unit -> site, for units without field data.
        units : list of str, optional
            Unit order. The default is the order of first appearance.
        """
        fleet = cls.__new__(cls)
        names = list(dict.fromkeys(field["unit"]))
        if shop is not None:
            names += [u for u in dict.fromkeys(shop["unit"]) if u not in names]
        if units is not None:
            names = list(units) + [u for u in names if u not in units]
        unit_sites = dict(zip(field["unit"], field["site"]))
        unit_sites.update(sites or {})
        unit_sites = {u: unit_sites.get(u, "site") for u in names}
        fleet._setup(
            field,
            shop,
            names,
            unit_sites,
            priors,
            freq,
            rows_per_bin,
            max_bins,
            max_head_slope,
        )
        return fleet

    def _setup(
        self,
        field,
        shop,
        names,
        sites,
        priors,
        freq,
        rows_per_bin,
        max_bins,
        max_head_slope=None,
    ):
        if max_head_slope is not None and not field.empty:
            field = field[field["head_slope"].abs() <= max_head_slope]
            if shop is not None:
                shop = shop[shop["head_slope"].abs() <= max_head_slope]
        self.max_head_slope = max_head_slope
        if len(names) < 2:
            raise ValueError("A fleet needs at least two units.")
        if field.empty:
            raise ValueError("The fleet has no field observations.")
        rows = field["unit"].value_counts()
        empty = [u for u in names if rows.get(u, 0) == 0]
        if empty:
            where = (
                f" (after leaving out the rows with |head_slope| > {max_head_slope})"
                if max_head_slope is not None
                else ""
            )
            warnings.warn(
                f"Units without field observations{where}: {empty}. Their "
                "as-built deviations come from their shop tests; their current "
                "level, rate, ranking and time to threshold are not estimated "
                "(NaN).",
                RuntimeWarning,
                stacklevel=3,
            )
        self.priors = priors or FleetPriors()
        self.units = list(names)
        self.sites = sites
        self.site_names = list(dict.fromkeys(sites[u] for u in self.units))
        field = field.sort_index()
        span_days = _days(field.index.max() - field.index.min())
        if freq is None:
            freq = FREQS[-1]
            for candidate in FREQS:
                if span_days / _days(candidate) <= max_bins:
                    freq = candidate
                    break
        self.freq = freq
        self.rows_per_bin = rows_per_bin
        start = field.index.min().floor("D")
        step = pd.Timedelta(freq)
        bins = np.floor((field.index - start) / step).astype(int)
        field = field.assign(bin=np.asarray(bins))
        if rows_per_bin:
            parts = []
            for _, group in field.groupby(["unit", "bin"], sort=False):
                if len(group) > rows_per_bin:
                    take = (
                        np.linspace(0, len(group) - 1, rows_per_bin).round().astype(int)
                    )
                    group = group.iloc[take]
                parts.append(group)
            field = pd.concat(parts).sort_index()
        self.n_bins = int(field["bin"].max()) + 1
        self.times = pd.DatetimeIndex([start + i * step for i in range(self.n_bins)])
        self.field = field
        self.shop = shop
        self.has_power = (
            "r_power" in field.columns and np.isfinite(field["r_power"]).any()
        )
        self.idata = None
        self._posterior = None
        self._divergences = None

    # model -----------------------------------------------------------------

    def model(self):
        """The PyMC model of the fleet."""
        pm = _require_pymc()
        import pytensor.tensor as pt

        p = self.priors
        n_units = len(self.units)
        unit_index = {u: i for i, u in enumerate(self.units)}
        site_index = {s: i for i, s in enumerate(self.site_names)}
        field = self.field
        u = field["unit"].map(unit_index).to_numpy()
        t = field["bin"].to_numpy()
        first_bin = (
            field.groupby("unit")["bin"].min().reindex(self.units).fillna(0).astype(int)
        )
        step_days = _days(self.freq)
        step_hours = _hours(self.freq)
        coords = {
            "unit": self.units,
            "site": self.site_names,
            "component": COMPONENTS,
            "field": FIELDS,
            "time": self.times,
            "step": np.arange(1, self.n_bins),
            "residual": RESIDUALS,
        }
        with pm.Model(coords=coords) as model:
            mu = pm.Normal(
                "mu", 0, np.array([p.mu_flow, p.mu_head, p.mu_eff]), dims="component"
            )
            tau_unit = pm.HalfNormal(
                "tau_unit",
                np.array([p.tau_unit_flow, p.tau_unit_head, p.tau_unit_eff]),
                dims="component",
            )
            # centred: shop tests and field data pin each unit, and the
            # non-centred form then couples tau_unit and z (poor mixing)
            theta = pm.Normal("theta", mu, tau_unit, dims=("unit", "component"))

            # centred offsets: shop and field data pin each unit's offset, and
            # the non-centred form then couples tau_install and z. The
            # Gamma prior (shape 2) keeps the scale off zero, where the
            # centred form funnels: field and shop always differ somewhat.
            install_scale = np.array([p.tau_install_head, p.tau_install_eff])
            tau_install = pm.Gamma(
                "tau_install", alpha=2.0, beta=2.0 / install_scale, dims="field"
            )
            offset = pm.Normal("install", 0, tau_install, dims=("unit", "field"))
            if len(self.site_names) > 1:
                tau_site = pm.HalfNormal(
                    "tau_site",
                    np.array([p.tau_site_head, p.tau_site_eff]),
                    dims="field",
                )
                z_site = pm.Normal("z_site", 0, 1, dims=("site", "field"))
                unit_site = np.array(
                    [site_index[self.sites[name]] for name in self.units]
                )
                offset = offset + (tau_site * z_site)[unit_site]
            field_offset = pm.Deterministic(
                "field_offset", offset, dims=("unit", "field")
            )

            mu_rate = pm.Normal(
                "mu_rate", 0, np.array([p.mu_rate_head, p.mu_rate_eff]), dims="field"
            )
            tau_rate = pm.HalfNormal(
                "tau_rate", np.array([p.tau_rate_head, p.tau_rate_eff]), dims="field"
            )
            z_rate = pm.Normal("z_rate", 0, 1, dims=("unit", "field"))
            rate = pm.Deterministic(
                "rate", mu_rate + tau_rate * z_rate, dims=("unit", "field")
            )
            if self.n_bins > 1:
                # zero-avoiding prior (Gamma, shape 4; 90 % between 0.34 and
                # 1.9 times the scale): with the centred walk, a scale that
                # can reach zero makes a funnel when the health is smooth
                walk_scale = np.array([p.sigma_walk_head, p.sigma_walk_eff])
                sigma_walk = pm.Gamma(
                    "sigma_walk", alpha=4.0, beta=4.0 / walk_scale, dims="field"
                )
                # centred walk: the level of each period is a parameter and
                # the steps beyond the degradation trend get the Student-t
                # prior. The data pin each period, which suits the centred
                # form (the non-centred form couples the drift and the steps).
                # The level is zero at each unit's first period.
                free = np.ones((n_units, 2, self.n_bins), dtype=bool)
                free[np.arange(n_units), :, first_bin.to_numpy()] = False
                # levels in units of 0.1 %: the samplers' starting jitter of +-1
                # on the unconstrained scale is then +-0.1 %, not +-100 %,
                # which would leave heavy-tailed steps a chain may never remove
                level_free = HEALTH_UNIT * pm.Normal(
                    "health_z", 0, 0.1 / HEALTH_UNIT, shape=int(free.sum())
                )
                raw = pt.set_subtensor(
                    pt.zeros((n_units, 2, self.n_bins))[np.nonzero(free)], level_free
                )
                # the health is zero on average over each unit's first
                # anchor_days with data: anchoring on one period lets a
                # heavy-tailed step right after it trade with the offset
                anchor = np.zeros((n_units, self.n_bins))
                n_anchor = max(1, int(np.ceil(ANCHOR_DAYS / step_days)))
                for i, name in enumerate(self.units):
                    bins = np.sort(field.loc[field["unit"] == name, "bin"].unique())
                    if len(bins) == 0:
                        bins = np.array([0])
                    window = bins[bins < bins[0] + n_anchor]
                    anchor[i, window] = 1 / len(window)
                health = raw - (raw * anchor[:, None, :]).sum(axis=2, keepdims=True)
                innovation = (
                    health[:, :, 1:]
                    - health[:, :, :-1]
                    - rate[:, :, None] * (step_hours / HOURS)
                )
                scale = sigma_walk[None, :, None] * np.sqrt(step_days)
                pm.Potential(
                    "walk",
                    pm.logp(
                        pm.StudentT.dist(nu=p.walk_nu, mu=0, sigma=scale), innovation
                    ).sum(),
                )
            else:
                health = pt.zeros((n_units, 2, 1))
            health = pm.Deterministic("health", health, dims=("unit", "field", "time"))

            bias_T = pm.Normal("bias_T", 0, p.bias_T, dims="unit")
            bias_pr = pm.Normal("bias_pr", 0, p.bias_pr, dims="unit")
            # the field data pin the flow term theta_flow + bias_flow and the
            # power balance pins bias_driver - bias_flow; sampling those
            # (same prior) avoids the -1 correlations of the plain form
            flow_field = pm.Normal("flow_field", theta[:, 0], p.bias_flow, dims="unit")
            bias_flow = pm.Deterministic(
                "bias_flow", flow_field - theta[:, 0], dims="unit"
            )
            sigma_noise = pm.HalfNormal(
                "sigma",
                np.array([p.noise_head, p.noise_eff, p.noise_power]),
                dims=("unit", "residual"),
            )
            floor = np.array(
                [p.model_error_head, p.model_error_eff, p.model_error_power]
            )
            sigma = pt.sqrt(sigma_noise**2 + floor**2)

            # transient disturbances of one period (process, ambient), not
            # carried to the next: without them a transient period needs two
            # opposite heavy-tailed walk steps, a second mode of the posterior
            sigma_period = pm.HalfNormal(
                "sigma_period",
                np.array([p.sigma_period_head, p.sigma_period_eff]),
                dims="field",
            )
            z_period = pm.Normal("z_period", 0, 1, dims=("unit", "field", "time"))
            period = sigma_period[None, :, None] * z_period

            flow = flow_field[u]
            level_head = (
                theta[u, 1] + field_offset[u, 0] + health[u, 0, t] + period[u, 0, t]
            )
            level_eff = (
                theta[u, 2] + field_offset[u, 1] + health[u, 1, t] + period[u, 1, t]
            )
            mean_head = (
                level_head
                - flow * field["head_slope"].to_numpy()
                + field["k_head_T"].to_numpy() * bias_T[u]
                + field["k_head_p"].to_numpy() * bias_pr[u]
            )
            mean_eff = (
                level_eff
                - flow * field["eff_slope"].to_numpy()
                + field["k_eff_T"].to_numpy() * bias_T[u]
                + field["k_eff_p"].to_numpy() * bias_pr[u]
            )
            pm.StudentT(
                "obs_head",
                nu=p.noise_nu,
                mu=mean_head,
                sigma=sigma[u, 0],
                observed=field["r_head"].to_numpy(),
            )
            pm.StudentT(
                "obs_eff",
                nu=p.noise_nu,
                mu=mean_eff,
                sigma=sigma[u, 1],
                observed=field["r_eff"].to_numpy(),
            )
            if self.has_power:
                power_level = pm.Normal(
                    "power_level", -bias_flow, p.bias_driver, dims="unit"
                )
                pm.Deterministic("bias_driver", power_level + bias_flow, dims="unit")
                rows = np.isfinite(field[["r_power", "w"]].to_numpy(dtype=float))
                rows = rows.all(axis=1)
                up = u[rows]
                power = field[rows]
                w = power["w"].to_numpy()
                mean_power = (
                    power_level[up]
                    + (1 - w) * bias_flow[up]
                    - w * bias_T[up] * power["k_power_T"].to_numpy()
                )
                pm.StudentT(
                    "obs_power",
                    nu=p.noise_nu,
                    mu=mean_power,
                    sigma=sigma[up, 2],
                    observed=power["r_power"].to_numpy(),
                )
            if self.shop is not None and len(self.shop):
                us = self.shop["unit"].map(unit_index).to_numpy()
                pm.Normal(
                    "shop_head",
                    theta[us, 1] - theta[us, 0] * self.shop["head_slope"].to_numpy(),
                    p.shop_head,
                    observed=self.shop["r_head"].to_numpy(),
                )
                pm.Normal(
                    "shop_eff",
                    theta[us, 2] - theta[us, 0] * self.shop["eff_slope"].to_numpy(),
                    p.shop_eff,
                    observed=self.shop["r_eff"].to_numpy(),
                )
        return model

    def fit(
        self,
        draws=1000,
        tune=1000,
        chains=4,
        random_seed=None,
        nuts_sampler=None,
        target_accept=0.95,
        progressbar=False,
        **kwargs,
    ):
        """Sample the posterior with NUTS.

        Parameters
        ----------
        draws, tune, chains : int, optional
            Draws kept per chain, tuning draws and number of chains.
        random_seed : int, optional
            Seed for reproducible draws.
        nuts_sampler : str, optional
            "nutpie" (the default when installed), "pymc", "numpyro" or
            "blackjax".
        target_accept : float, optional
            Target acceptance rate of NUTS. The default, 0.95, takes smaller
            steps than PyMC's 0.8: the few variance parameters of a fleet
            (2 to 6 units) give a posterior with varying curvature, where
            the default step diverges.
        **kwargs
            Passed to ``pymc.sample``.

        Returns
        -------
        Fleet
            ``self``, with the posterior. A ``RuntimeWarning`` is issued when
            :meth:`diagnostics` finds R-hat above 1.01 or divergences.
        """
        pm = _require_pymc()
        if nuts_sampler is None:
            try:
                import nutpie  # noqa: F401

                nuts_sampler = "nutpie"
            except ImportError:
                nuts_sampler = "pymc"
        model = self.model()
        with model:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                idata = pm.sample(
                    draws=draws,
                    tune=tune,
                    chains=chains,
                    random_seed=random_seed,
                    nuts_sampler=nuts_sampler,
                    target_accept=target_accept,
                    progressbar=progressbar,
                    **kwargs,
                )
        self.idata = idata
        self._posterior = _posterior_dataset(idata)
        diverging = _sample_stat(idata, "diverging")
        self._divergences = int(np.sum(diverging)) if diverging is not None else 0
        # warns when the chains have not converged
        self.diagnostics()
        return self

    # results ---------------------------------------------------------------

    @property
    def posterior(self):
        if self._posterior is None:
            raise RuntimeError("Fit the fleet first (Fleet.fit()).")
        return self._posterior

    def _draws(self, name):
        """Draws of a variable as an array (sample, ...)."""
        values = np.asarray(self.posterior[name].values)
        return values.reshape(-1, *values.shape[2:])

    def _last_bins(self):
        last = self.field.groupby("unit")["bin"].max()
        return np.array([int(last.get(u, self.n_bins - 1)) for u in self.units])

    def current(self):
        """Draws of the current head and efficiency levels (sample, unit, field).

        The level at each unit's last period with data: the deviation from
        the vendor curve after removing the flow-capacity shift and the
        instrument biases. NaN for units without field observations (the
        level would come from the priors only).
        """
        theta = self._draws("theta")
        offset = self._draws("field_offset")
        health = self._draws("health")
        last = self._last_bins()
        at_last = np.stack(
            [health[:, i, :, last[i]] for i in range(len(self.units))], axis=1
        )
        current = theta[:, :, 1:] + offset + at_last
        current[:, ~self._has_field(), :] = np.nan
        return current

    def _field_rows(self):
        """Number of field observations per unit, in unit order."""
        rows = self.field["unit"].value_counts()
        return np.array([int(rows.get(u, 0)) for u in self.units])

    def _has_field(self):
        """True for the units with field observations, in unit order."""
        return self._field_rows() > 0

    def diagnostics(self, warn=True):
        """Rank-normalised split R-hat and bulk effective sample size.

        Of the parameters and of the health levels (the levels fixed at zero
        by the anchoring are left out), with the number of divergent
        transitions.

        Parameters
        ----------
        warn : bool, optional
            Issue a ``RuntimeWarning`` when the maximum R-hat is above 1.01
            or there are divergences. The default is True.

        Returns
        -------
        dict
            ``max_rhat``, ``min_ess``, ``divergences`` and a table per
            parameter element (``rhat``, ``ess``).
        """
        rows = []
        for name in DIAGNOSTIC_VARIABLES:
            if name not in self.posterior:
                continue
            values = np.asarray(self.posterior[name].values)
            flat = values.reshape(values.shape[0], values.shape[1], -1)
            for j in range(flat.shape[2]):
                x = flat[:, :, j]
                if np.ptp(x) == 0:
                    continue
                rows.append(
                    {
                        "parameter": f"{name}[{j}]",
                        "rhat": _split_rhat(x),
                        "ess": _ess(x),
                    }
                )
        table = pd.DataFrame(rows, columns=["parameter", "rhat", "ess"])
        table = table.set_index("parameter")
        result = {
            "max_rhat": float(table["rhat"].max()),
            "min_ess": float(table["ess"].min()),
            "divergences": self._divergences,
            "table": table,
        }
        if warn:
            problems = []
            if result["max_rhat"] > MAX_RHAT:
                worst = table["rhat"].idxmax()
                problems.append(
                    f"R-hat {result['max_rhat']:.3f} > {MAX_RHAT} ({worst})"
                )
            if self._divergences:
                problems.append(f"{self._divergences} divergent transitions")
            if problems:
                warnings.warn(
                    "The fleet posterior may be unreliable: "
                    + "; ".join(problems)
                    + ". Sample longer (more tune and draws) or check the data.",
                    RuntimeWarning,
                    stacklevel=2,
                )
        return result

    @staticmethod
    def _interval(x, prob=0.9, axis=0):
        lo, hi = (1 - prob) / 2, 1 - (1 - prob) / 2
        return (
            np.mean(x, axis=axis),
            np.quantile(x, lo, axis=axis),
            np.quantile(x, hi, axis=axis),
        )

    def summary(self, prob=0.9, threshold=-0.03):
        """Per-unit results with ``prob`` credible intervals.

        Deviations are in percent of the vendor curve (efficiency in
        points), rates in percent (points) per 1000 h.

        Parameters
        ----------
        prob : float, optional
            Probability of the credible intervals. The default is 0.9.
        threshold : float, optional
            Efficiency level (fraction) for ``p_below_threshold``. The
            default is -0.03 (3 points below the vendor curve).

        Returns
        -------
        pandas.DataFrame
        """
        theta = self._draws("theta")
        offset = self._draws("field_offset")
        rate = self._draws("rate")
        has_field = self._has_field()
        rate[:, ~has_field, :] = np.nan
        current = self.current()
        # the worst among the units with field data
        worst = np.argmin(
            np.where(has_field[None, :], current[:, :, 1], np.inf), axis=1
        )
        rows = {}
        for i, unit in enumerate(self.units):
            row = {"site": self.sites[unit]}

            def put(name, x):
                m, lo, hi = self._interval(x * 100, prob)
                row[name] = m
                row[f"{name}_low"] = lo
                row[f"{name}_high"] = hi

            put("asbuilt_flow", theta[:, i, 0])
            put("asbuilt_head", theta[:, i, 1])
            put("asbuilt_eff", theta[:, i, 2])
            put("field_offset_head", offset[:, i, 0])
            put("field_offset_eff", offset[:, i, 1])
            put("current_head", current[:, i, 0])
            put("current_eff", current[:, i, 1])
            put("rate_head", rate[:, i, 0])
            put("rate_eff", rate[:, i, 1])
            if has_field[i]:
                row["p_worst_eff"] = float(np.mean(worst == i))
                row["p_below_threshold"] = float(np.mean(current[:, i, 1] < threshold))
                row["p_degrading_eff"] = float(np.mean(rate[:, i, 1] < 0))
            else:
                row["p_worst_eff"] = np.nan
                row["p_below_threshold"] = np.nan
                row["p_degrading_eff"] = np.nan
            row["field_rows"] = int(self._field_rows()[i])
            bias_t = self._draws("bias_T")[:, i]
            row["bias_T"] = float(np.mean(bias_t))
            row["bias_flow"] = float(np.mean(self._draws("bias_flow")[:, i]) * 100)
            if "bias_driver" in self.posterior:
                row["bias_driver"] = float(
                    np.mean(self._draws("bias_driver")[:, i]) * 100
                )
            rows[unit] = row
        return pd.DataFrame(rows).T.rename_axis("unit")

    def fleet_scatter(self, prob=0.9):
        """Design-level mean deviation and scatter between units, in percent."""
        rows = {}

        def put(name, x):
            m, lo, hi = self._interval(np.asarray(x) * 100, prob)
            rows[name] = {"mean": m, "low": lo, "high": hi}

        for j, c in enumerate(COMPONENTS):
            put(f"mu_{c}", self._draws("mu")[:, j])
            put(f"tau_unit_{c}", self._draws("tau_unit")[:, j])
        for j, f in enumerate(FIELDS):
            put(f"tau_install_{f}", self._draws("tau_install")[:, j])
            put(f"mu_rate_{f}", self._draws("mu_rate")[:, j])
            put(f"tau_rate_{f}", self._draws("tau_rate")[:, j])
            if "tau_site" in self.posterior:
                put(f"tau_site_{f}", self._draws("tau_site")[:, j])
        return pd.DataFrame(rows).T

    def health(self, unit, prob=0.9):
        """Level of head and efficiency of a unit over time (percent).

        Returns
        -------
        pandas.DataFrame
            Indexed by period, with mean, low and high of ``head`` and
            ``eff`` and the corrected observations (period medians of the
            residuals minus the fitted flow and instrument terms).
        """
        i = self.units.index(unit)
        level = (
            self._draws("theta")[:, i, 1:, None]
            + self._draws("field_offset")[:, i, :, None]
            + self._draws("health")[:, i]
        )
        out = pd.DataFrame(index=self.times)
        for j, f in enumerate(FIELDS):
            m, lo, hi = self._interval(level[:, j] * 100, prob)
            out[f], out[f"{f}_low"], out[f"{f}_high"] = m, lo, hi
        corrected = self._corrected(unit)
        for f in FIELDS:
            out[f"{f}_observed"] = (
                corrected.groupby("bin")[f]
                .median()
                .reindex(range(self.n_bins))
                .to_numpy()
                * 100
            )
        return out

    def _corrected(self, unit):
        """Observations of a unit minus the posterior-mean flow and instrument terms."""
        i = self.units.index(unit)
        rows = self.field[self.field["unit"] == unit]
        flow = np.mean(self._draws("theta")[:, i, 0] + self._draws("bias_flow")[:, i])
        bias_t = np.mean(self._draws("bias_T")[:, i])
        bias_p = np.mean(self._draws("bias_pr")[:, i])
        head = (
            rows["r_head"]
            + flow * rows["head_slope"]
            - rows["k_head_T"] * bias_t
            - rows["k_head_p"] * bias_p
        )
        eff = (
            rows["r_eff"]
            + flow * rows["eff_slope"]
            - rows["k_eff_T"] * bias_t
            - rows["k_eff_p"] * bias_p
        )
        return pd.DataFrame({"head": head, "eff": eff, "bin": rows["bin"]})

    def ranking(self, field="eff"):
        """Probability of each rank (1 = worst) of the current level per unit."""
        j = FIELDS.index(field)
        has_field = self._has_field()
        current = self.current()[:, has_field, j]
        order = np.argsort(np.argsort(current, axis=1), axis=1) + 1
        n = int(has_field.sum())
        ranks = np.full((len(self.units), n), np.nan)
        ranks[has_field] = np.array(
            [np.mean(order == k, axis=0) for k in range(1, n + 1)]
        ).T.reshape(n, n)
        return pd.DataFrame(
            ranks,
            index=pd.Index(self.units, name="unit"),
            columns=[f"rank_{k}" for k in range(1, n + 1)],
        )

    def events(self, threshold=3.0, prob=0.99):
        """Health steps larger than ``threshold`` random-walk scales.

        Returns
        -------
        pandas.DataFrame
            One row per unit, field and period where the step beyond the
            degradation trend exceeds ``threshold`` random-walk scales with
            posterior probability above ``prob``: the step size (percent,
            positive for a recovery such as a wash) and its probability.
        """
        columns = ["unit", "field", "time", "step", "probability"]
        if self.n_bins < 2:
            return pd.DataFrame(columns=columns)
        health = self._draws("health")  # sample, unit, field, time
        rate = self._draws("rate")
        sigma = self._draws("sigma_walk")
        step_days = _days(self.freq)
        steps = np.diff(health, axis=3) - rate[:, :, :, None] * (
            _hours(self.freq) / HOURS
        )
        z = steps / (sigma[:, None, :, None] * np.sqrt(step_days))
        p_up = np.mean(z > threshold, axis=0)
        p_down = np.mean(z < -threshold, axis=0)
        rows = []
        found = (p_up > prob) | (p_down > prob)
        found[~self._has_field()] = False
        for i, j, k in zip(*np.nonzero(found)):
            rows.append(
                {
                    "unit": self.units[i],
                    "field": FIELDS[j],
                    "time": self.times[k + 1],
                    "step": float(np.mean(steps[:, i, j, k]) * 100),
                    "probability": float(max(p_up[i, j, k], p_down[i, j, k])),
                }
            )
        return pd.DataFrame(rows, columns=columns)

    def time_to_threshold(self, threshold=-0.03, field="eff", horizon_hours=8760.0):
        """Posterior of the time until each unit's level reaches ``threshold``.

        Extrapolates each draw's current level with its degradation rate.

        Returns
        -------
        pandas.DataFrame
            Per unit: median and 5 % / 95 % quantiles of the hours to the
            threshold (inf when it is not reached), and the probability of
            reaching it within ``horizon_hours``. NaN for units without field
            observations.
        """
        j = FIELDS.index(field)
        current = self.current()[:, :, j]
        rate = self._draws("rate")[:, :, j] / HOURS
        gap = threshold - current
        with np.errstate(divide="ignore", invalid="ignore"):
            hours = np.where(gap >= 0, 0.0, np.where(rate < 0, gap / rate, np.inf))

        def quantile(q):
            # an order statistic, not an interpolation: between a finite
            # value and inf numpy would interpolate to inf - inf = NaN
            return np.quantile(hours, q, axis=0, method="inverted_cdf")

        has_field = self._has_field()
        out = pd.DataFrame(
            {
                "median_h": np.median(hours, axis=0),
                "q05_h": quantile(0.05),
                "q95_h": quantile(0.95),
                "p_within_horizon": np.mean(hours <= horizon_hours, axis=0),
            },
            index=pd.Index(self.units, name="unit"),
        )
        out.loc[~has_field, :] = np.nan
        return out

    # plots -----------------------------------------------------------------

    def plot_units(self, prob=0.9):
        """Forest plot of the as-built and current head and efficiency per unit."""
        import plotly.graph_objects as go
        import plotly.io as pio
        from plotly.subplots import make_subplots

        s = self.summary(prob=prob)
        template = pio.templates[pio.templates.default]
        colors = list(template.layout.colorway or ["#1f77b4", "#ff7f0e"])
        fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Head (%)", "Efficiency (points)"),
            shared_yaxes=True,
        )
        for col, f in enumerate(FIELDS, start=1):
            for k, (name, label, symbol) in enumerate(
                (
                    (f"asbuilt_{f}", "as built", "diamond"),
                    (f"current_{f}", "current", "circle"),
                )
            ):
                color = colors[k % len(colors)]
                fig.add_trace(
                    go.Scatter(
                        x=s[name].astype(float),
                        y=s.index,
                        mode="markers",
                        marker=dict(symbol=symbol, size=9, color=color),
                        name=label,
                        legendgroup=label,
                        showlegend=col == 1,
                        error_x=dict(
                            type="data",
                            symmetric=False,
                            array=(s[f"{name}_high"] - s[name]).astype(float),
                            arrayminus=(s[name] - s[f"{name}_low"]).astype(float),
                            color=color,
                        ),
                    ),
                    row=1,
                    col=col,
                )
            fig.add_vline(x=0, line_width=1, line_dash="dot", row=1, col=col)
        fig.update_layout(margin=dict(t=40))
        fig.update_xaxes(title_text="deviation from the vendor curve")
        return fig

    def plot_health(self, field="eff", prob=0.9):
        """Level of each unit over time with its credible band."""
        import plotly.graph_objects as go

        fig = go.Figure()
        for unit in self.units:
            h = self.health(unit, prob=prob)
            x = list(h.index) + list(h.index[::-1])
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=list(h[f"{field}_high"]) + list(h[f"{field}_low"][::-1]),
                    fill="toself",
                    opacity=0.2,
                    line=dict(width=0),
                    name=f"{unit} band",
                    legendgroup=unit,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=h.index, y=h[field], mode="lines", name=unit, legendgroup=unit
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=h.index,
                    y=h[f"{field}_observed"],
                    mode="markers",
                    marker=dict(size=4, opacity=0.5),
                    name=f"{unit} data",
                    legendgroup=unit,
                    showlegend=False,
                )
            )
        unit_label = "points" if field == "eff" else "%"
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title=(
                f"{'Efficiency' if field == 'eff' else 'Head'} deviation ({unit_label})"
            ),
        )
        return fig

    # persistence -----------------------------------------------------------

    def save(self, path):
        """Save observations, settings and posterior draws to a zip file."""
        posterior = {}
        arrays = {}
        if self._posterior is not None:
            for name, var in self._posterior.data_vars.items():
                arrays[name] = np.asarray(var.values)
                posterior[name] = list(var.dims)
        meta = {
            "units": self.units,
            "sites": self.sites,
            "freq": self.freq,
            "rows_per_bin": self.rows_per_bin,
            "max_head_slope": self.max_head_slope,
            "priors": asdict(self.priors),
            "posterior_dims": posterior,
            "divergences": self._divergences,
        }
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("meta.json", json.dumps(meta))
            z.writestr("field.parquet", self.field.to_parquet())
            if self.shop is not None:
                z.writestr("shop.parquet", self.shop.to_parquet())
            if arrays:
                buffer = io.BytesIO()
                np.savez_compressed(buffer, **arrays)
                z.writestr("posterior.npz", buffer.getvalue())

    @classmethod
    def load(cls, path):
        """Load a fleet saved with :meth:`save`."""
        import xarray as xr

        with zipfile.ZipFile(path) as z:
            meta = json.loads(z.read("meta.json"))
            field = pd.read_parquet(io.BytesIO(z.read("field.parquet")))
            shop = (
                pd.read_parquet(io.BytesIO(z.read("shop.parquet")))
                if "shop.parquet" in z.namelist()
                else None
            )
            arrays = (
                dict(np.load(io.BytesIO(z.read("posterior.npz"))))
                if "posterior.npz" in z.namelist()
                else {}
            )
        fleet = cls.__new__(cls)
        fleet._setup(
            field.drop(columns=["bin"]),
            shop,
            meta["units"],
            meta["sites"],
            FleetPriors(**meta["priors"]),
            meta["freq"],
            None,  # the saved rows are already thinned
            None,
        )
        fleet.rows_per_bin = meta["rows_per_bin"]
        fleet.max_head_slope = meta.get("max_head_slope")
        if arrays:
            fleet._posterior = xr.Dataset(
                {name: (meta["posterior_dims"][name], arrays[name]) for name in arrays}
            )
            fleet._divergences = meta.get("divergences")
        return fleet

    def to_dict(self, prob=0.9, threshold=-0.03):
        """JSON-ready results for reports and the web app."""

        def frame(df):
            return json.loads(df.to_json(orient="split", date_format="iso"))

        diag = self.diagnostics(warn=False)
        return {
            "units": self.units,
            "sites": self.sites,
            "freq": self.freq,
            "summary": frame(self.summary(prob=prob, threshold=threshold)),
            "scatter": frame(self.fleet_scatter(prob=prob)),
            "ranking": frame(self.ranking()),
            "events": frame(self.events()),
            "time_to_threshold": frame(self.time_to_threshold(threshold=threshold)),
            "health": {u: frame(self.health(u, prob=prob)) for u in self.units},
            "diagnostics": {
                "max_rhat": diag["max_rhat"],
                "min_ess": diag["min_ess"],
                "divergences": diag["divergences"],
            },
        }


def simulate_fleet(
    n_units=4,
    n_sites=2,
    days=360,
    rows_per_day=6,
    shop=True,
    power=True,
    wash_day=None,
    priors=None,
    seed=None,
    truth=None,
):
    """Synthetic fleet observations with known truth.

    Draws the unit deviations, rates and instrument biases from the priors
    (or takes them from ``truth``), simulates operating points across the
    curve, a slow random walk with an optional wash (a step up of the
    efficiency and head of the first unit at ``wash_day``) and noisy
    residuals.

    Returns
    -------
    field : pandas.DataFrame
        Field observations (see :func:`field_observations`) with ``unit`` and
        ``site`` columns.
    shop : pandas.DataFrame or None
        Shop observations.
    truth : dict
        The values used.
    """
    rng = np.random.default_rng(seed)
    p = priors or FleetPriors()
    units = [f"U{i + 1}" for i in range(n_units)]
    sites = {u: f"S{i % n_sites + 1}" for i, u in enumerate(units)}
    if truth is None:
        mu = np.array([0.01, 0.005, -0.01]) + rng.normal(0, 0.005, 3)
        theta = mu + rng.normal(0, [0.015, 0.015, 0.01], size=(n_units, 3))
        site_effect = {s: rng.normal(0, 0.01, 2) for s in sorted(set(sites.values()))}
        install = rng.normal(0, 0.01, size=(n_units, 2))
        offset = np.array([site_effect[sites[u]] for u in units]) + install
        rate = rng.normal(-0.004, 0.002, size=(n_units, 2)) * np.array([0.5, 1.0])
        truth = {
            "units": units,
            "sites": sites,
            "theta": theta,
            "field_offset": offset,
            "rate": rate,
            "bias_T": rng.normal(0, 0.3, n_units),
            "bias_pr": rng.normal(0, 0.002, n_units),
            "bias_flow": rng.normal(0, 0.008, n_units),
            "bias_driver": rng.normal(0, 0.015, n_units),
            "wash": None,
        }
    walk_scale = 0.0005
    start = pd.Timestamp("2025-01-01")
    frames = []
    truth["health"] = {}
    for i, unit in enumerate(units):
        n = days * rows_per_day
        hours = np.sort(rng.uniform(0, _hours(f"{days}D"), n))
        time = start + pd.to_timedelta(hours, unit="h")
        day = (hours // _hours("1D")).astype(int)
        walk = np.cumsum(rng.normal(0, walk_scale, size=(days, 2)), axis=0)
        health = walk[day] + truth["rate"][i] * hours[:, None] / HOURS
        if wash_day is not None and i == 0:
            jump = np.array([0.01, 0.02])
            health = health + np.where(day[:, None] >= wash_day, jump, 0.0)
            truth["wash"] = {"unit": unit, "day": wash_day, "step": jump}
        daily = walk + truth["rate"][i] * (
            (np.arange(days)[:, None] + 0.5) * _hours("1D") / HOURS
        )
        if wash_day is not None and i == 0:
            daily = daily + np.where(np.arange(days)[:, None] >= wash_day, jump, 0.0)
        truth["health"][unit] = pd.DataFrame(
            daily,
            index=start + pd.to_timedelta(np.arange(days), unit="D"),
            columns=FIELDS,
        )
        # operating points: position on the curve sets the slopes
        x = rng.uniform(0, 1, n)
        head_slope = -0.1 - 0.6 * x**2
        eff_slope = 0.15 - 0.45 * x
        Ts = rng.normal(310, 4, n)
        pr = rng.uniform(1.6, 2.6, n)
        eff_true = 0.78
        Td = Ts * pr ** (0.3 / 1.3 / eff_true)
        ps = rng.normal(20e5, 1e5, n)
        sens = _sensitivities(np.full(n, eff_true), ps, Ts, ps * pr, Td)
        flow = truth["theta"][i, 0] + truth["bias_flow"][i]
        level = truth["theta"][i, 1:] + truth["field_offset"][i] + health
        r_head = (
            level[:, 0]
            - flow * head_slope
            + sens["k_head_T"] * truth["bias_T"][i]
            + sens["k_head_p"] * truth["bias_pr"][i]
            + 0.006 * rng.standard_t(p.noise_nu, n)
        )
        r_eff = (
            level[:, 1]
            - flow * eff_slope
            + sens["k_eff_T"] * truth["bias_T"][i]
            + sens["k_eff_p"] * truth["bias_pr"][i]
            + 0.006 * rng.standard_t(p.noise_nu, n)
        )
        frame = pd.DataFrame(
            {
                "r_head": r_head,
                "r_eff": r_eff,
                "head_slope": head_slope,
                "eff_slope": eff_slope,
                **sens,
                "unit": unit,
                "site": sites[unit],
            },
            index=time,
        )
        if power:
            w = np.full(n, 0.98)
            frame["w"] = w
            frame["r_power"] = (
                truth["bias_driver"][i]
                - w * (truth["bias_flow"][i] + truth["bias_T"][i] * sens["k_power_T"])
                + 0.008 * rng.standard_t(p.noise_nu, n)
            )
        frames.append(frame)
    field = pd.concat(frames).sort_index()
    shop_frame = None
    if shop:
        rows = []
        for i, unit in enumerate(units):
            for x in np.linspace(0.05, 0.95, 6):
                head_slope = -0.1 - 0.6 * x**2
                eff_slope = 0.15 - 0.45 * x
                rows.append(
                    {
                        "r_head": truth["theta"][i, 1]
                        - truth["theta"][i, 0] * head_slope
                        + rng.normal(0, 0.003),
                        "r_eff": truth["theta"][i, 2]
                        - truth["theta"][i, 0] * eff_slope
                        + rng.normal(0, 0.003),
                        "head_slope": head_slope,
                        "eff_slope": eff_slope,
                        "unit": unit,
                    }
                )
        shop_frame = pd.DataFrame(rows)
    return field, shop_frame, truth
