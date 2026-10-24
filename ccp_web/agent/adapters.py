"""Per-page adapters of the agent API: start, results and figures.

The API (``api.py``) is generic over the page type; what a page calculates
and shows lives in one module per page app, looked up here by app type and
imported lazily (``ADAPTERS``), so a page app without an adapter only makes
its calculate/results/figures endpoints answer 501.

Adapter interface
-----------------

Each module (``ccp_web/<app>/agent.py``) exposes:

``start(case, params) -> Job``
    Start the page's calculation exactly as its button does: the SAME
    validation and ``jobs.start_job`` call, shared with the view (refactor
    the view so both call one function). ``params`` is the JSON object the
    agent sent (``{}`` when none); reject unknown params. Raise
    ``units.InputError(errors)`` for invalid inputs (400, ``details.errors``
    maps state keys to messages, as the page highlights them) or
    ``ValueError`` for bad params (400). Never accept or forward secrets (PI
    password, AI key): when a run needs one, raise ``ValueError`` saying the
    user must start it in the browser.

``results(case) -> dict``
    What the results section shows, as JSON: plain numbers (floats, not
    Quantities), units explicit in the column names or in a ``units`` map.
    ``{"available": False, "reason": "..."}`` when nothing is computed yet.
    Build it from the services the results view uses, not from rendered
    HTML. Pass it through ``json_safe`` (NaN/inf become null).

``figures(case) -> list[dict]``
    ``[{"id", "title", "section"}]`` of the figures the page shows; ``[]``
    when there are none yet. Ids are URL-safe (letters, digits, ``_``,
    ``-``). Cheap: do not build the figures here.

``figure(case, figure_id) -> plotly Figure | dict``
    One figure, built on demand. Raise ``KeyError`` for an unknown id (404).
    The API converts it with ``figure_data`` / ``figure_json``.

Optional:

``has_results(case) -> bool``
    Cheap check for ``GET cases/<pk>``; defaults to "the case has an
    artifact".

``PARAMS = {name: description}``
    The ``calculate`` params, listed by ``GET schema/<app_type>``.
"""

import base64
import datetime
import decimal
import importlib
import importlib.util
import math

import numpy as np

ADAPTERS = {
    "straight_through": "ccp_web.performance_test.agent",
    "back_to_back": "ccp_web.performance_test.agent",
    "curves_conversion": "ccp_web.curves.agent",
    "performance_evaluation": "ccp_web.evaluation.agent",
    "curves_digitizer": "ccp_web.digitizer.agent",
}
SIGNIFICANT_DIGITS = 6


class AdapterMissing(LookupError):
    """No agent adapter for this app type (the API answers 501)."""


def get_adapter(app_type):
    """The adapter module of ``app_type``; ``AdapterMissing`` if there is none.

    Only a missing adapter module counts as "not implemented"; an import
    error inside an existing adapter is a bug and propagates.
    """
    name = ADAPTERS.get(app_type)
    if name is None:
        raise AdapterMissing(f"not implemented for this app type ({app_type})")
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name == name:
            raise AdapterMissing(
                f"not implemented for this app type ({app_type})"
            ) from None
        raise


def has_adapter(app_type):
    try:
        get_adapter(app_type)
    except AdapterMissing:
        return False
    return True


def has_results(case):
    """Whether the page has results to show, without building them."""
    try:
        adapter = get_adapter(case.app_type)
    except AdapterMissing:
        adapter = None
    check = getattr(adapter, "has_results", None)
    if check is not None:
        return bool(check(case))
    return case.artifacts.exists()


# --------------------------------------------------------------------------
# JSON-safe values
# --------------------------------------------------------------------------


def _number(value, digits=None):
    value = float(value)
    if not math.isfinite(value):
        return None
    if digits:
        return float(f"{value:.{digits}g}")
    return value


def _typed_array(value):
    """Decode plotly's ``{"dtype", "bdata", "shape"?}`` typed array, or None."""
    if not (isinstance(value, dict) and "bdata" in value and "dtype" in value):
        return None
    try:
        array = np.frombuffer(
            base64.b64decode(value["bdata"]), dtype=np.dtype(value["dtype"])
        )
        shape = value.get("shape")
        if shape:
            if isinstance(shape, str):
                shape = [int(s) for s in shape.split(",")]
            array = array.reshape(shape)
    except (TypeError, ValueError):
        return None
    return array


def json_safe(value, digits=None):
    """``value`` with only JSON types: NaN/inf -> None, numpy -> Python.

    Quantities become ``{"value", "units"}`` so a unit is never dropped
    silently; dates become ISO strings. ``digits`` rounds floats to that many
    significant digits.
    """
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating, decimal.Decimal)):
        return _number(value, digits)
    if isinstance(value, dict):
        array = _typed_array(value)
        if array is not None:
            return json_safe(array, digits)
        return {str(k): json_safe(v, digits) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        if value.dtype.kind in "fc":
            return [json_safe(v, digits) for v in value.tolist()]
        return json_safe(value.tolist(), digits)
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(v, digits) for v in value]
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if hasattr(value, "magnitude") and hasattr(value, "units"):  # pint Quantity
        return {
            "value": json_safe(value.magnitude, digits),
            "units": f"{value.units:~}" or str(value.units),
        }
    if hasattr(value, "isoformat"):  # pandas Timestamp, numpy datetime64 wrappers
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, np.datetime64):
        return str(value)
    if hasattr(value, "to_dict"):  # pandas objects
        return json_safe(value.to_dict(), digits)
    return str(value)


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------


def _as_figure(fig):
    import plotly.graph_objects as go

    if isinstance(fig, go.Figure):
        return fig
    return go.Figure(fig)


def _title(obj):
    """Text of a plotly title (a string or ``{"text": ...}``), or None."""
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj or None
    text = getattr(obj, "text", None)
    if text is None and isinstance(obj, dict):
        text = obj.get("text")
    return text or None


def figure_data(fig, digits=SIGNIFICANT_DIGITS):
    """Compact figure for an agent: titles and the traces' points.

    ``{title, x_title, y_title, traces: [{name, type, mode, x, y}]}``, floats
    rounded to ``digits`` significant digits. Secondary axes, when present,
    are listed in ``axes``.
    """
    fig = _as_figure(fig)
    layout = fig.layout
    traces = []
    for trace in fig.data:
        item = {
            "name": getattr(trace, "name", None),
            "type": trace.type,
            "mode": getattr(trace, "mode", None),
        }
        for axis in ("x", "y", "z"):
            values = getattr(trace, axis, None)
            if values is not None:
                item[axis] = json_safe(values, digits)
        for ref in ("xaxis", "yaxis"):
            value = getattr(trace, ref, None)
            if value and value not in ("x", "y"):
                item[ref] = value
        traces.append(item)
    data = {
        "title": _title(layout.title),
        "x_title": _title(layout.xaxis.title),
        "y_title": _title(layout.yaxis.title),
        "traces": traces,
    }
    axes = {}
    for name in layout:
        if (name.startswith("xaxis") or name.startswith("yaxis")) and name not in (
            "xaxis",
            "yaxis",
        ):
            axis = layout[name]
            if axis is not None and _title(axis.title):
                axes[name] = _title(axis.title)
    if axes:
        data["axes"] = axes
    return data


def figure_json(fig, template=False):
    """Full plotly figure as plain JSON (typed arrays decoded to lists).

    The theme template is dropped unless ``template``: it is most of the
    bytes and none of the content.
    """
    import json

    data = json.loads(_as_figure(fig).to_json())
    if not template:
        data.get("layout", {}).pop("template", None)
    return json_safe(data)


def kaleido_available():
    return importlib.util.find_spec("kaleido") is not None


def figure_png(fig, width=900, height=550):
    """PNG bytes of a figure; ``NotImplementedError`` without kaleido."""
    if not kaleido_available():
        raise NotImplementedError(
            "PNG export needs the optional 'kaleido' package; use format=data or "
            "format=plotly"
        )
    return _as_figure(fig).to_image(format="png", width=width, height=height)
