"""Compute services for the straight-through compressor page.

Hydrates :class:`ccp.compressor.Point1Sec` and :class:`ccp.compressor.StraightThrough`
instances from a form-data dict, then produces the plotly figures that the
Django templates embed with ``{% plotly_figure %}``.

All compressor math is delegated to :mod:`apps.core.services.ccp_service`
(with a local stub fallback). This module only coordinates unit conversion,
gas-composition lookup and plot assembly.
"""

from __future__ import annotations

import logging
from typing import Any

import ccp
from ccp.config.utilities import r_getattr

try:
    from apps.core.services import ccp_service  # type: ignore
except Exception:  # pragma: no cover - stub fallback
    from apps.straight_through._stubs import ccp_service  # type: ignore

try:
    from apps.core.services.parameter_map import PARAMETERS  # type: ignore
except Exception:  # pragma: no cover
    PARAMETERS = {}

Q_ = ccp.Q_
LOG = logging.getLogger(__name__)

CURVES = ("head", "eff", "discharge_pressure", "power")
TEST_PARAMETERS = (
    "flow",
    "suction_pressure",
    "suction_temperature",
    "discharge_pressure",
    "discharge_temperature",
    "casing_delta_T",
    "speed",
    "balance_line_flow_m",
    "seal_gas_flow_m",
    "seal_gas_temperature",
    "oil_flow_journal_bearing_de",
    "oil_flow_journal_bearing_nde",
    "oil_flow_thrust_bearing_nde",
    "oil_inlet_temperature",
    "oil_outlet_temperature_de",
    "oil_outlet_temperature_nde",
)


def _q(value: Any, units: str) -> Any:
    """Return ``value`` as a pint :class:`~ccp.Q_` with the given units.

    Empty strings and ``None`` return ``None`` so the caller can branch on
    missing data. Numeric strings are coerced via :class:`float`.
    """
    if value in (None, ""):
        return None
    return Q_(float(value), units)


def _is_mass_flow(units: str) -> bool:
    """Return True when *units* has a ``[mass]/[time]`` dimensionality."""
    return Q_(0, units).dimensionality == Q_(0, "kg/s").dimensionality


def _flow_kwarg(value: Any, units: str) -> dict[str, Any]:
    """Map a flow magnitude/units pair into the right ``flow_m``/``flow_v`` kwarg."""
    quantity = _q(value, units)
    if quantity is None:
        return {}
    key = "flow_m" if _is_mass_flow(units) else "flow_v"
    return {key: quantity}


def _gas_for(form_data: dict, point_key: str) -> dict[str, float]:
    """Return the gas composition to use for *point_key*.

    Parameters
    ----------
    form_data : dict
        Flat dict of form values keyed like ``gas_point_1``.
    point_key : str
        Either ``"point_guarantee"`` or ``"point_{i}"``.
    """
    composition = form_data.get(f"gas_{point_key}") or form_data.get("gas_composition")
    if isinstance(composition, dict) and composition:
        return composition
    return {"methane": 1.0}


def _build_guarantee(form_data: dict, options: dict) -> ccp.Point:
    """Create the :class:`ccp.Point` guarantee point from form data."""
    units = form_data.get("data_sheet_units", {})
    gas = _gas_for(form_data, "point_guarantee")

    kwargs: dict[str, Any] = {}
    kwargs.update(
        _flow_kwarg(
            form_data.get("flow_point_guarantee"),
            units.get("flow", "kg/h"),
        )
    )
    kwargs["suc"] = ccp.State(
        p=_q(form_data.get("suction_pressure_point_guarantee"), units.get("suction_pressure", "bar")),
        T=_q(form_data.get("suction_temperature_point_guarantee"), units.get("suction_temperature", "degK")),
        fluid=gas,
    )
    kwargs["disch"] = ccp.State(
        p=_q(form_data.get("discharge_pressure_point_guarantee"), units.get("discharge_pressure", "bar")),
        T=_q(form_data.get("discharge_temperature_point_guarantee"), units.get("discharge_temperature", "degK")),
        fluid=gas,
    )
    kwargs["speed"] = _q(form_data.get("speed_point_guarantee"), units.get("speed", "rpm"))
    kwargs["b"] = _q(form_data.get("b_point_guarantee"), units.get("b", "mm"))
    kwargs["D"] = _q(form_data.get("D_point_guarantee"), units.get("D", "mm"))

    if options.get("bearing_mechanical_losses"):
        power = _q(form_data.get("power_point_guarantee"), units.get("power", "kW"))
        shaft = _q(
            form_data.get("power_shaft_point_guarantee") or form_data.get("power_point_guarantee"),
            units.get("power_shaft", "kW"),
        )
        kwargs["power_losses"] = (shaft - power) if power is not None and shaft is not None else Q_(0, "W")
    else:
        kwargs["power_losses"] = Q_(0, "W")

    return ccp_service.build_guarantee_point(**kwargs)


def _build_test_points(form_data: dict, options: dict) -> list:
    """Create :class:`ccp.compressor.Point1Sec` objects for every populated test point."""
    units = form_data.get("test_units", {})
    ds_units = form_data.get("data_sheet_units", {})
    geometry = {
        "b": _q(form_data.get("b_point_guarantee"), ds_units.get("b", "mm")),
        "D": _q(form_data.get("D_point_guarantee"), ds_units.get("D", "mm")),
        "casing_area": _q(
            form_data.get("casing_area_point_guarantee"),
            ds_units.get("casing_area", "m²"),
        ),
        "surface_roughness": _q(
            form_data.get("surface_roughness_point_guarantee"),
            ds_units.get("surface_roughness", "mm"),
        ),
    }

    test_points: list = []
    for i in range(1, 7):
        flow_raw = form_data.get(f"flow_point_{i}")
        p_suc = form_data.get(f"suction_pressure_point_{i}")
        T_suc = form_data.get(f"suction_temperature_point_{i}")
        if not flow_raw or not p_suc or not T_suc:
            continue

        gas = _gas_for(form_data, f"point_{i}")
        kwargs: dict[str, Any] = dict(geometry)
        kwargs.update(_flow_kwarg(flow_raw, units.get("flow", "kg/h")))
        kwargs["suc"] = ccp.State(
            p=_q(p_suc, units.get("suction_pressure", "bar")),
            T=_q(T_suc, units.get("suction_temperature", "degK")),
            fluid=gas,
        )
        kwargs["disch"] = ccp.State(
            p=_q(form_data.get(f"discharge_pressure_point_{i}"), units.get("discharge_pressure", "bar")),
            T=_q(form_data.get(f"discharge_temperature_point_{i}"), units.get("discharge_temperature", "degK")),
            fluid=gas,
        )
        kwargs["speed"] = _q(form_data.get(f"speed_point_{i}"), units.get("speed", "rpm"))

        casing_delta = form_data.get(f"casing_delta_T_point_{i}")
        if casing_delta and options.get("casing_heat_loss"):
            kwargs["casing_temperature"] = _q(casing_delta, units.get("casing_delta_T", "delta_degC"))
            kwargs["ambient_temperature"] = 0
        else:
            kwargs["casing_temperature"] = 0
            kwargs["ambient_temperature"] = 0

        if options.get("calculate_leakages"):
            kwargs["balance_line_flow_m"] = _q(
                form_data.get(f"balance_line_flow_m_point_{i}"),
                units.get("balance_line_flow_m", "kg/h"),
            )
            if options.get("seal_gas_flow"):
                kwargs["seal_gas_flow_m"] = _q(
                    form_data.get(f"seal_gas_flow_m_point_{i}"),
                    units.get("seal_gas_flow_m", "kg/h"),
                ) or Q_(0, units.get("seal_gas_flow_m", "kg/h"))
                kwargs["seal_gas_temperature"] = _q(
                    form_data.get(f"seal_gas_temperature_point_{i}"),
                    units.get("seal_gas_temperature", "degK"),
                ) or Q_(0, units.get("seal_gas_temperature", "degK"))

        kwargs["bearing_mechanical_losses"] = bool(options.get("bearing_mechanical_losses"))

        test_points.append(ccp_service.build_point_1sec(**kwargs))

    return test_points


def _build_curve_figures(straight_through, point_interpolated, plot_limits, show_points) -> dict:
    """Build the head/eff/discharge/power plotly figures."""
    plots: dict = {}
    for curve in CURVES:
        limits = plot_limits.get(curve, {})
        flow_v_units = limits.get("x", {}).get("units") or "m³/h"
        curve_units = limits.get("y", {}).get("units")

        kwargs: dict[str, Any] = {"flow_v_units": flow_v_units}
        if curve_units:
            if curve == "discharge_pressure":
                kwargs["p_units"] = curve_units
            else:
                kwargs[f"{curve}_units"] = curve_units

        method = "disch.p" if curve == "discharge_pressure" else curve

        fig = r_getattr(straight_through, f"{method}_plot")(show_points=show_points, **kwargs)
        fig = r_getattr(point_interpolated, f"{method}_plot")(
            fig=fig, show_points=show_points, **kwargs
        )
        fig.update_layout(
            showlegend=True,
            legend=dict(yanchor="bottom", y=0.01, xanchor="left", x=0.01),
        )
        plots[curve] = fig
    return plots


def run_straight_through(form_data: dict, options: dict | None = None) -> dict[str, Any]:
    """Run the full straight-through calculation for a form submission.

    Parameters
    ----------
    form_data : dict
        Flat key/value pairs mirroring the Streamlit ``session_state``
        (guarantee point, six test points, gas composition, unit selections).
    options : dict, optional
        Sidebar toggles: ``reynolds_correction``, ``casing_heat_loss``,
        ``bearing_mechanical_losses``, ``calculate_leakages``,
        ``seal_gas_flow``, ``variable_speed``, ``show_points``,
        ``calculate_speed``.

    Returns
    -------
    dict
        Mapping containing ``straight_through`` (the model), ``figures``
        (plotly figures keyed by ``head``/``eff``/``discharge_pressure``/
        ``power``/``mach``/``reynolds``), ``speed_operational_rpm`` and a
        flat ``results`` dict with per-test-point diagnostic columns.
    """
    options = dict(options or {})
    guarantee_point = _build_guarantee(form_data, options)
    test_points = _build_test_points(form_data, options)

    straight_through = ccp_service.build_straight_through(
        guarantee_point=guarantee_point,
        test_points=test_points,
        reynolds_correction=bool(options.get("reynolds_correction", True)),
        bearing_mechanical_losses=bool(options.get("bearing_mechanical_losses", False)),
        calculate_speed=bool(options.get("calculate_speed", False)),
    )

    point_interpolated = straight_through.point(
        flow_v=straight_through.guarantee_point.flow_v,
        speed=straight_through.speed_operational,
    )

    figures = _build_curve_figures(
        straight_through,
        point_interpolated,
        form_data.get("plot_limits", {}),
        bool(options.get("show_points", False)),
    )
    figures["mach"] = point_interpolated.plot_mach()
    figures["reynolds"] = point_interpolated.plot_reynolds()

    results = {
        "phi_t": [round(p.phi.m, 5) for p in straight_through.test_points],
        "mach_t": [round(p.mach.m, 5) for p in straight_through.test_points],
        "re_t": [round(p.reynolds.m, 5) for p in straight_through.test_points],
        "head_kj_kg": [
            round(p.head.to("kJ/kg").m, 5) for p in straight_through.points_flange_sp
        ],
        "power_kw": [
            round(p.power_shaft.to("kW").m, 5) for p in straight_through.points_rotor_t
        ],
    }

    return {
        "straight_through": straight_through,
        "figures": figures,
        "speed_operational_rpm": float(straight_through.speed_operational.to("rpm").m),
        "results": results,
    }
