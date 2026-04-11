"""Thin wrappers around the ``ccp`` library for Django views.

Every wrapper is a pure function: no Django imports, no Streamlit state, no
caching side-effects. Each function optionally honours a ``polytropic_method``
keyword argument by setting ``ccp.config.POLYTROPIC_METHOD`` before delegating
to the underlying ``ccp`` object. Callers that need to batch several wrappers
under the same polytropic method should pass the kwarg on each call for
explicitness.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import ccp
from ccp.compressor import BackToBack, Point1Sec, StraightThrough
from ccp.impeller import Impeller
from ccp.state import State

from apps.core.services.polytropic_methods import (
    POLYTROPIC_METHODS,
    get_polytropic_methods,
)


def _apply_polytropic_method(method: str | None) -> None:
    """Update ``ccp.config.POLYTROPIC_METHOD`` in-place if *method* is given.

    Accepts either a UI label from :data:`POLYTROPIC_METHODS` or the raw
    ``ccp.config`` value. Unknown values are forwarded verbatim so callers
    that want to experiment with new methods are not blocked.
    """
    if method is None:
        return
    resolved = POLYTROPIC_METHODS.get(method, method)
    ccp.config.POLYTROPIC_METHOD = resolved


def build_gas_state(composition: dict[str, float], p: Any, T: Any) -> State:
    """Construct a :class:`ccp.State` from a composition dict and p/T.

    Parameters
    ----------
    composition : dict of str to float
        Component name to molar fraction. Must be non-empty.
    p : pint.Quantity or float
        Absolute pressure. If a bare float is supplied, ``ccp.State`` will
        interpret it as Pa.
    T : pint.Quantity or float
        Absolute temperature. If a bare float is supplied, ``ccp.State`` will
        interpret it as degK.

    Returns
    -------
    ccp.State
        Newly constructed state.
    """
    if not composition:
        raise ValueError("composition must contain at least one component")
    return State(p=p, T=T, fluid=dict(composition))


def build_point_1sec(
    *, polytropic_method: str | None = None, **kwargs: Any
) -> Point1Sec:
    """Construct a :class:`ccp.compressor.Point1Sec`.

    Parameters
    ----------
    polytropic_method : str, optional
        UI label or raw ``ccp.config`` value. If provided, is applied to
        ``ccp.config.POLYTROPIC_METHOD`` before instantiation.
    **kwargs
        Forwarded directly to ``Point1Sec``.

    Returns
    -------
    ccp.compressor.Point1Sec
    """
    _apply_polytropic_method(polytropic_method)
    return Point1Sec(**kwargs)


def build_straight_through(
    guarantee_point: Point1Sec,
    test_points: Iterable[Point1Sec],
    *,
    polytropic_method: str | None = None,
    **opts: Any,
) -> StraightThrough:
    """Construct a :class:`ccp.compressor.StraightThrough` compressor.

    Parameters
    ----------
    guarantee_point : ccp.compressor.Point1Sec
        Guarantee operating point.
    test_points : iterable of ccp.compressor.Point1Sec
        Measured test points used for the performance curves.
    polytropic_method : str, optional
        UI label or raw ``ccp.config`` value.
    **opts
        Additional keyword arguments forwarded to ``StraightThrough``
        (``speed_operational``, ``reynolds_correction``,
        ``bearing_mechanical_losses``...).

    Returns
    -------
    ccp.compressor.StraightThrough
    """
    _apply_polytropic_method(polytropic_method)
    return StraightThrough(
        guarantee_point=guarantee_point,
        test_points=list(test_points),
        **opts,
    )


def build_back_to_back(
    guarantee_point_sec1: Any,
    test_points_sec1: Iterable[Any],
    guarantee_point_sec2: Any,
    test_points_sec2: Iterable[Any],
    *,
    polytropic_method: str | None = None,
    **opts: Any,
) -> BackToBack:
    """Construct a :class:`ccp.compressor.BackToBack` compressor.

    Parameters
    ----------
    guarantee_point_sec1, guarantee_point_sec2 : ccp.compressor.PointFirstSection / PointSecondSection
        Guarantee points for the two sections.
    test_points_sec1, test_points_sec2 : iterable
        Per-section test points.
    polytropic_method : str, optional
        UI label or raw ``ccp.config`` value.
    **opts
        Additional keyword arguments forwarded to ``BackToBack``.

    Returns
    -------
    ccp.compressor.BackToBack
    """
    _apply_polytropic_method(polytropic_method)
    return BackToBack(
        guarantee_point_sec1=guarantee_point_sec1,
        test_points_sec1=list(test_points_sec1),
        guarantee_point_sec2=guarantee_point_sec2,
        test_points_sec2=list(test_points_sec2),
        **opts,
    )


def load_impeller_from_engauge_csv(
    files: dict[str, Any] | list,
    suction_state: State,
    *,
    polytropic_method: str | None = None,
    **kwargs: Any,
) -> Impeller:
    """Build an :class:`ccp.Impeller` from Engauge-digitised CSV files.

    Parameters
    ----------
    files : dict or list
        Either a mapping with keys ``curve_name`` and ``curve_path`` (pointing
        at the directory containing ``<name>-head.csv`` and ``<name>-eff.csv``)
        or a two-item list ``[curve_name, curve_path]``. For backwards
        compatibility a dict of additional kwargs is also accepted and will be
        merged into *kwargs*.
    suction_state : ccp.State
        Suction state used when evaluating the curves.
    polytropic_method : str, optional
        UI label or raw ``ccp.config`` value.
    **kwargs
        Additional keyword arguments forwarded to
        :meth:`ccp.Impeller.load_from_engauge_csv`.

    Returns
    -------
    ccp.Impeller
    """
    _apply_polytropic_method(polytropic_method)

    if isinstance(files, dict):
        curve_name = files.get("curve_name")
        curve_path = files.get("curve_path")
        extra = {
            k: v for k, v in files.items() if k not in ("curve_name", "curve_path")
        }
        kwargs = {**extra, **kwargs}
    elif isinstance(files, (list, tuple)) and len(files) == 2:
        curve_name, curve_path = files
    else:
        raise TypeError(
            "files must be a dict with curve_name/curve_path or a [name, path] pair"
        )

    if curve_name is None or curve_path is None:
        raise ValueError("curve_name and curve_path are required")

    return Impeller.load_from_engauge_csv(
        suc=suction_state,
        curve_name=curve_name,
        curve_path=Path(curve_path),
        **kwargs,
    )


def convert_impeller(
    impeller: Impeller | list[Impeller],
    *,
    polytropic_method: str | None = None,
    **kwargs: Any,
) -> Impeller:
    """Convert an impeller's performance map to a new suction condition.

    Parameters
    ----------
    impeller : ccp.Impeller or list of ccp.Impeller
        Source impeller(s). Forwarded to :meth:`ccp.Impeller.convert_from`.
    polytropic_method : str, optional
        UI label or raw ``ccp.config`` value.
    **kwargs
        Forwarded to :meth:`ccp.Impeller.convert_from` (``suc``, ``find``,
        ``speed``).

    Returns
    -------
    ccp.Impeller
    """
    _apply_polytropic_method(polytropic_method)
    return Impeller.convert_from(impeller, **kwargs)


def build_evaluation(
    *, polytropic_method: str | None = None, **kwargs: Any
) -> ccp.Evaluation:
    """Construct a :class:`ccp.Evaluation` object.

    Parameters
    ----------
    polytropic_method : str, optional
        UI label or raw ``ccp.config`` value.
    **kwargs
        Forwarded directly to ``ccp.Evaluation``.

    Returns
    -------
    ccp.Evaluation
    """
    _apply_polytropic_method(polytropic_method)
    return ccp.Evaluation(**kwargs)


def polytropic_methods() -> dict[str, str]:
    """Return the label-to-value mapping for polytropic methods.

    Returns
    -------
    dict of str to str
        Fresh copy of :data:`POLYTROPIC_METHODS`.
    """
    return get_polytropic_methods()
