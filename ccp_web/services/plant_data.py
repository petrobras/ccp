"""Plant data for the performance evaluation: PI historian, files and mock data.

The PI helpers are ported from ``ccp/app/common.py``. ``pandaspi`` (the
Petrobras PI Web API client) is optional: without it the PI source reports an
error and the file and mock sources still work.

Every source returns a tz-naive ``DatetimeIndex`` DataFrame with the ccp
column names (``ps, Ts, pd, Td, speed`` and ``flow_v`` or
``delta_p, p_downstream``, plus optional ``fluid_<component>`` columns).
"""

import io
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import ccp
from ccp import Q_

log = logging.getLogger("ccp_web.plant_data")

TEST_DATA = Path(ccp.__file__).parent / "tests" / "data"
PI_TIME_SPAN = "450s"

KEY_TO_COLUMN = {
    "suc_p_tag": "ps",
    "suc_p_tag_2": "ps_2",
    "suc_T_tag": "Ts",
    "suc_T_tag_2": "Ts_2",
    "disch_p_tag": "pd",
    "disch_p_tag_2": "pd_2",
    "disch_T_tag": "Td",
    "disch_T_tag_2": "Td_2",
    "speed_tag": "speed",
    "speed_tag_2": "speed_2",
    "flow_tag": "flow_v",
    "flow_tag_2": "flow_v_2",
    "delta_p_tag": "delta_p",
    "delta_p_tag_2": "delta_p_2",
    "p_downstream_tag": "p_downstream",
    "p_downstream_tag_2": "p_downstream_2",
}

PARAMETER_MAP = [
    ("ps", "suc_p_tag", "suc_p_tag_2", "suc_p_unit", "suc_p_unit_2"),
    ("Ts", "suc_T_tag", "suc_T_tag_2", "suc_T_unit", "suc_T_unit_2"),
    ("pd", "disch_p_tag", "disch_p_tag_2", "disch_p_unit", "disch_p_unit_2"),
    ("Td", "disch_T_tag", "disch_T_tag_2", "disch_T_unit", "disch_T_unit_2"),
    ("speed", "speed_tag", "speed_tag_2", "speed_unit", "speed_unit_2"),
    ("flow_v", "flow_tag", "flow_tag_2", "flow_unit", "flow_unit_2"),
    ("delta_p", "delta_p_tag", "delta_p_tag_2", "delta_p_unit", "delta_p_unit_2"),
    (
        "p_downstream",
        "p_downstream_tag",
        "p_downstream_tag_2",
        "p_downstream_unit",
        "p_downstream_unit_2",
    ),
]


class PlantDataError(RuntimeError):
    pass


def has_pandaspi():
    try:
        import pandaspi  # noqa: F401
    except ImportError:
        return False
    return True


def tag_mappings(state, pi_password=None):
    """Tag configuration from a case state (``common.build_tag_mappings``)."""
    get = state.get
    tm = {
        "pi_server_name": get("pi_server_name", ""),
        "pi_auth_method": get("pi_auth_method") or "kerberos",
    }
    for prefix in ["suc_p", "suc_T", "disch_p", "disch_T", "speed"]:
        for n in ["", "_2"]:
            tm[f"{prefix}_tag{n}"] = get(f"{prefix}_tag{n}", "") or ""
            tm[f"{prefix}_unit{n}"] = get(f"{prefix}_unit{n}")
    if tm["pi_auth_method"] == "basic":
        tm["pi_login"] = (get("pi_username", ""), pi_password or "")
    else:
        tm["pi_login"] = None
    if (get("flow_method") or "Direct") == "Direct":
        prefixes = ["flow"]
    else:
        prefixes = ["delta_p", "p_downstream"]
    for prefix in prefixes:
        for n in ["", "_2"]:
            tm[f"{prefix}_tag{n}"] = get(f"{prefix}_tag{n}", "") or ""
            tm[f"{prefix}_unit{n}"] = get(f"{prefix}_unit{n}")
    if get("fluid_source") == "Inform Component Tags":
        fluid_tags, fluid_units = {}, {}
        for i in range(12):
            comp = get(f"fluid_component_{i}", "")
            tag = get(f"fluid_tag_{i}", "")
            if comp and tag:
                fluid_tags[comp] = tag
                fluid_units[comp] = get(f"fluid_unit_{i}") or "mol_frac"
        tm["fluid_tags"] = fluid_tags
        tm["fluid_units"] = fluid_units
    return tm


def data_units(state, tm):
    """Units of the data columns (``common.build_data_units``)."""
    units = {
        "ps": state.get("suc_p_unit") or "bar",
        "Ts": state.get("suc_T_unit") or "degC",
        "pd": state.get("disch_p_unit") or "bar",
        "Td": state.get("disch_T_unit") or "degC",
        "speed": state.get("speed_unit") or "rpm",
    }
    for comp, unit in tm.get("fluid_units", {}).items():
        if unit == "ppm":
            units[f"fluid_{comp}"] = "ppm"
    if (state.get("flow_method") or "Direct") == "Direct":
        units["flow_v"] = state.get("flow_unit") or "m³/h"
    else:
        units["delta_p"] = state.get("delta_p_unit") or "bar"
        units["p_downstream"] = state.get("p_downstream_unit") or "bar"
    return units


def build_pi_query(tm):
    tags, rename, alias = [], {}, {}

    def add(tag, col):
        if not tag:
            return
        if tag not in tags:
            tags.append(tag)
        existing = rename.get(tag)
        if existing is None:
            rename[tag] = col
        elif existing != col:
            alias[col] = existing

    for key, col in KEY_TO_COLUMN.items():
        add(tm.get(key, ""), col)
    for comp, tag in tm.get("fluid_tags", {}).items():
        add(tag, f"fluid_{comp}")
    return tags, rename, alias


def format_pi_time(dt):
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def apply_fluid_unit_conversions(df, tm):
    for comp, unit in tm.get("fluid_units", {}).items():
        col = f"fluid_{comp}"
        if col in df.columns and unit == "percent":
            df[col] = df[col] / 100.0
    return df


def sanitize_pi_dataframe(df):
    """Drop PI error rows, strip the timezone and coerce to numbers."""
    error_columns = {}
    for col in df.columns:
        if df[col].dtype == object:
            is_dict = df[col].apply(lambda v: isinstance(v, dict))
            if is_dict.any():
                n = int(is_dict.sum())
                sample = df[col][is_dict].iloc[0]
                if n == len(df):
                    raise PlantDataError(
                        f"Tag mapped to column '{col}' returned only PI system values "
                        f"(instrument error). Sample value: {sample}. "
                        "Please check if the instrument is operational."
                    )
                error_columns[col] = (n, sample)
    if error_columns:
        mask = pd.Series(False, index=df.index)
        for col, (n, sample) in error_columns.items():
            log.warning(
                "Column %r: %d/%d rows contain PI system values (e.g. %s); dropped.",
                col,
                n,
                len(df),
                sample,
            )
            mask |= df[col].apply(lambda v: isinstance(v, dict))
        df = df[~mask].copy()
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def frozen_series_mask(series, min_points=10, min_seconds=4500):
    """Samples in runs of identical values (>= 10 samples or > 4500 s)."""
    s = series.copy()
    valid = s.notna()
    if not valid.any():
        return pd.Series(False, index=series.index)
    group_id = s.ne(s.shift()).cumsum()
    frozen_by_points = s.groupby(group_id).transform("size") >= min_points
    frozen_by_time = pd.Series(False, index=series.index)
    if isinstance(series.index, pd.DatetimeIndex):
        for _, idx in series.groupby(group_id).groups.items():
            idx = list(idx)
            if len(idx) >= 2 and (idx[-1] - idx[0]).total_seconds() > min_seconds:
                frozen_by_time.loc[idx] = True
    return valid & (frozen_by_points | frozen_by_time)


def merge_redundant_parameter_tags(df, tm):
    """Merge the optional second tag of each parameter into the first."""
    for col, tag1_key, tag2_key, unit1_key, unit2_key in PARAMETER_MAP:
        tag2 = tm.get(tag2_key, "")
        col2 = f"{col}_2"
        if col not in df.columns and col2 in df.columns:
            df[col] = df[col2]
        if col not in df.columns:
            continue
        s1 = pd.to_numeric(df[col], errors="coerce")
        s1_valid = s1.where(s1.notna() & (s1 != 0) & ~frozen_series_mask(s1))
        if tag2 and col2 in df.columns:
            s2 = pd.to_numeric(df[col2], errors="coerce")
            s2_valid = s2.where(s2.notna() & (s2 != 0) & ~frozen_series_mask(s2))
            unit1 = tm.get(unit1_key)
            unit2 = tm.get(unit2_key) or unit1
            if unit1 and unit2 and unit1 != unit2:
                try:
                    s2_valid = s2_valid.apply(lambda v: Q_(v, unit2).to(unit1).m)
                except Exception as exc:
                    log.warning(
                        "Unit conversion failed for %s (%s -> %s): %s",
                        col,
                        unit2,
                        unit1,
                        exc,
                    )
                    s2_valid = pd.Series(np.nan, index=s2_valid.index)
            merged = s1_valid.copy()
            both = s1_valid.notna() & s2_valid.notna()
            only_second = s1_valid.isna() & s2_valid.notna()
            merged[both] = (s1_valid[both] + s2_valid[both]) / 2.0
            merged[only_second] = s2_valid[only_second]
            df[col] = merged
        else:
            df[col] = s1_valid
        if col2 in df.columns:
            df = df.drop(columns=[col2])
    return df


def _pi_session(tm, start, end):
    try:
        from pandaspi import SessionWeb
    except ImportError as exc:
        raise PlantDataError(
            "The PI data source needs the pandaspi package, which is only available "
            "inside Petrobras. Use the File or Mock data source instead."
        ) from exc
    tags, rename, alias = build_pi_query(tm)
    if not tags:
        raise PlantDataError("No PI tags configured. Please fill in the tag names.")
    session = SessionWeb(
        server_name=tm.get("pi_server_name", ""),
        login=tm.get("pi_login"),
        tags=tags,
        time_range=(format_pi_time(start), format_pi_time(end)),
        time_span=PI_TIME_SPAN,
        authentication=tm.get("pi_auth_method", "kerberos"),
    )
    df = session.df.rename(columns=rename)
    df = sanitize_pi_dataframe(df)
    for alias_col, source_col in alias.items():
        if source_col in df.columns:
            df[alias_col] = df[source_col]
    df = merge_redundant_parameter_tags(df, tm)
    return apply_fluid_unit_conversions(df, tm)


def _mock_frame(tm):
    name = "data_delta_p.parquet" if tm.get("delta_p_tag") else "data.parquet"
    return pd.read_parquet(TEST_DATA / name)


def read_data_file(name, content):
    """Plant data from an uploaded CSV or Parquet file.

    The first column (or a ``time``/``timestamp`` column) is the timestamp;
    the other columns must already use the ccp names (``ps, Ts, pd, Td,
    speed, flow_v`` or ``delta_p, p_downstream``, ``fluid_<component>``) in
    the units configured in the Tags section.
    """
    lower = name.lower()
    if lower.endswith(".parquet"):
        df = pd.read_parquet(io.BytesIO(content))
    elif lower.endswith((".csv", ".txt")):
        df = pd.read_csv(io.BytesIO(content))
        time_col = next(
            (
                c
                for c in df.columns
                if str(c).lower() in ("time", "timestamp", "datetime", "date")
            ),
            df.columns[0],
        )
        df = df.set_index(time_col)
    else:
        raise PlantDataError("Plant data files must be .csv or .parquet.")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, format="mixed")
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df.sort_index()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def fetch(source, tm, start=None, end=None, file=None):
    """Historical data for ``[start, end]``.

    Parameters
    ----------
    source : {"pi", "file", "mock"}
    file : (name, bytes), optional
        The uploaded plant data file for the ``file`` source.
    """
    end = end or datetime.now()
    start = start or end - timedelta(hours=1)
    if source == "mock":
        return _mock_frame(tm)
    if source == "file":
        if not file:
            raise PlantDataError("Upload a plant data file (CSV or Parquet) first.")
        df = read_data_file(*file)
        return df[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))]
    return _pi_session(tm, start, end)


def fetch_online(source, tm, file=None):
    """The latest three samples (15 minutes of 7.5-minute data)."""
    now = datetime.now()
    if source == "mock":
        df = _mock_frame(tm)
        df = df[df["speed"] > 9000].reset_index(drop=True)
        max_start = len(df) - 3
        sample = (
            df.copy()
            if max_start <= 0
            else df.iloc[(i := random.randint(0, max_start)) : i + 3].copy()
        )
        stamps = [
            now - timedelta(minutes=15),
            now - timedelta(minutes=7, seconds=30),
            now,
        ]
        sample.index = pd.DatetimeIndex(stamps[: len(sample)])
        return sample
    if source == "file":
        if not file:
            raise PlantDataError("Upload a plant data file (CSV or Parquet) first.")
        return read_data_file(*file).tail(3)
    return _pi_session(tm, now - timedelta(minutes=15), now)
