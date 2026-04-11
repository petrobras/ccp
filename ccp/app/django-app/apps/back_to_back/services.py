"""Service layer for the back-to-back compressor page.

This module is the direct port of the large ``main()`` body in
``ccp/app/pages/2_back_to_back.py``. It takes the dict produced by the Django
forms (shape described in :func:`run_back_to_back`), constructs
``ccp.compressor.PointFirstSection`` / ``PointSecondSection`` instances, and
delegates the heavy lifting to
:func:`apps.core.services.ccp_service.build_back_to_back`.

The return value is a pure-Python dict suitable for JSON serialisation /
template context: compute figures (``fig_head_sec1``, ``fig_power_sec2`` …)
and a results table per section.
"""

from __future__ import annotations

from typing import Any

try:
    from apps.core.services import ccp_service
except Exception:  # noqa: BLE001 - stubs layer installs a substitute
    from apps.back_to_back._stubs import bootstrap as _stub_bootstrap

    _stub_bootstrap.install()
    from apps.core.services import ccp_service  # type: ignore[no-redef]

try:
    from apps.core.services.gas_composition import get_gas_composition
except Exception:  # noqa: BLE001

    def get_gas_composition(name, table, defaults):  # type: ignore[no-redef]
        return {"methane": 1.0}


try:
    from apps.core.services.polytropic_methods import POLYTROPIC_METHODS
except Exception:  # noqa: BLE001
    POLYTROPIC_METHODS = {"Sandberg-Colby": "sandberg_colby"}


import ccp
from ccp.compressor import PointFirstSection, PointSecondSection

Q_ = ccp.Q_

CURVE_NAMES = ("head", "eff", "discharge_pressure", "power")
SECTION_KEYS = ("sec1", "sec2")

_SUBSCRIPT_T = "\u209c"
_SUBSCRIPT_SP = "\u209b\u209a"
_SUPERSCRIPT_CONV = "\u1d9c\u1d52\u207f\u1d5b"


def _as_float(value: Any) -> float | None:
    """Parse *value* as a float, treating blanks and ``None`` as missing."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if "," in text:
        raise ValueError("Please use '.' as decimal separator")
    return float(text)


def _q(value: Any, units: str | None):
    """Wrap *value* in ``ccp.Q_`` if non-empty, else return ``None``."""
    magnitude = _as_float(value)
    if magnitude is None or not units:
        return None
    return Q_(magnitude, units)


def _guarantee_kwargs(data: dict, *, bearing_mechanical_losses: bool) -> dict:
    """Build ``ccp.Point`` kwargs for a guarantee point."""
    units = data["units"]
    values = data["values"]
    fluid = data["fluid"]

    kwargs: dict[str, Any] = {}
    flow_units = units.get("flow")
    if flow_units and Q_(0, flow_units).dimensionality == "[mass] / [time]":
        kwargs["flow_m"] = _q(values.get("flow"), flow_units)
    else:
        kwargs["flow_v"] = _q(values.get("flow"), flow_units)

    kwargs["suc"] = ccp.State(
        p=_q(values["suction_pressure"], units["suction_pressure"]),
        T=_q(values["suction_temperature"], units["suction_temperature"]),
        fluid=fluid,
    )
    kwargs["disch"] = ccp.State(
        p=_q(values["discharge_pressure"], units["discharge_pressure"]),
        T=_q(values["discharge_temperature"], units["discharge_temperature"]),
        fluid=fluid,
    )
    kwargs["speed"] = _q(values["speed"], units["speed"])
    kwargs["b"] = _q(values["b"], units["b"])
    kwargs["D"] = _q(values["D"], units["D"])

    power_guarantee = _q(values.get("power"), units.get("power"))
    if bearing_mechanical_losses:
        power_shaft_text = values.get("power_shaft") or values.get("power")
        power_shaft_units = units.get("power_shaft") or units.get("power")
        power_shaft = _q(power_shaft_text, power_shaft_units)
        if power_shaft is not None and power_guarantee is not None:
            kwargs["power_losses"] = power_shaft.to("kW") - power_guarantee.to("kW")
        else:
            kwargs["power_losses"] = Q_(0, "W")
    else:
        kwargs["power_losses"] = Q_(0, "W")
    return kwargs


def _test_point_kwargs(
    test_point: dict,
    guarantee: dict,
    *,
    casing_heat_loss: bool,
    calculate_leakages: bool,
    seal_gas_flow: bool,
    bearing_mechanical_losses: bool,
    is_first_section: bool,
) -> dict:
    """Build ``PointFirstSection`` / ``PointSecondSection`` kwargs."""
    units = test_point["units"]
    values = test_point["values"]
    fluid = test_point["fluid"]

    kwargs: dict[str, Any] = {}
    flow_units = units.get("flow")
    if flow_units and Q_(0, flow_units).dimensionality == "[mass] / [time]":
        kwargs["flow_m"] = _q(values.get("flow"), flow_units)
    else:
        kwargs["flow_v"] = _q(values.get("flow"), flow_units)

    kwargs["suc"] = ccp.State(
        p=_q(values["suction_pressure"], units["suction_pressure"]),
        T=_q(values["suction_temperature"], units["suction_temperature"]),
        fluid=fluid,
    )
    kwargs["disch"] = ccp.State(
        p=_q(values["discharge_pressure"], units["discharge_pressure"]),
        T=_q(values["discharge_temperature"], units["discharge_temperature"]),
        fluid=fluid,
    )

    casing_delta = _q(values.get("casing_delta_T"), units.get("casing_delta_T"))
    if casing_heat_loss and casing_delta is not None:
        kwargs["casing_temperature"] = casing_delta
        kwargs["ambient_temperature"] = 0
    else:
        kwargs["casing_temperature"] = 0
        kwargs["ambient_temperature"] = 0

    if calculate_leakages:
        kwargs["balance_line_flow_m"] = _q(
            values.get("balance_line_flow_m"), units.get("balance_line_flow_m")
        )
        seal_flow_units = units.get("seal_gas_flow_m") or "kg/s"
        if seal_gas_flow:
            kwargs["seal_gas_flow_m"] = _q(
                values.get("seal_gas_flow_m"), seal_flow_units
            ) or Q_(0, seal_flow_units)
        else:
            kwargs["seal_gas_flow_m"] = Q_(0, seal_flow_units)

        if is_first_section:
            kwargs["div_wall_flow_m"] = _q(
                values.get("div_wall_flow_m"), units.get("div_wall_flow_m")
            )
            kwargs["first_section_discharge_flow_m"] = _q(
                values.get("first_section_discharge_flow_m"),
                units.get("first_section_discharge_flow_m"),
            )
            kwargs["end_seal_upstream_pressure"] = _q(
                values.get("end_seal_upstream_pressure"),
                units.get("end_seal_upstream_pressure"),
            )
            kwargs["end_seal_upstream_temperature"] = _q(
                values.get("end_seal_upstream_temperature"),
                units.get("end_seal_upstream_temperature"),
            )
            kwargs["div_wall_upstream_pressure"] = _q(
                values.get("div_wall_upstream_pressure"),
                units.get("div_wall_upstream_pressure"),
            )
            kwargs["div_wall_upstream_temperature"] = _q(
                values.get("div_wall_upstream_temperature"),
                units.get("div_wall_upstream_temperature"),
            )
            seal_temp_units = units.get("seal_gas_temperature") or "degK"
            if seal_gas_flow:
                kwargs["seal_gas_temperature"] = _q(
                    values.get("seal_gas_temperature"), seal_temp_units
                ) or Q_(0, seal_temp_units)
            else:
                kwargs["seal_gas_temperature"] = Q_(0, seal_temp_units)

    kwargs["bearing_mechanical_losses"] = bearing_mechanical_losses
    if bearing_mechanical_losses:
        for oil_key in (
            "oil_flow_journal_bearing_de",
            "oil_flow_journal_bearing_nde",
            "oil_flow_thrust_bearing_nde",
            "oil_inlet_temperature",
            "oil_outlet_temperature_de",
            "oil_outlet_temperature_nde",
        ):
            kwargs[oil_key] = _q(values.get(oil_key), units.get(oil_key))

    kwargs["b"] = _q(guarantee["values"]["b"], guarantee["units"]["b"])
    kwargs["D"] = _q(guarantee["values"]["D"], guarantee["units"]["D"])
    kwargs["casing_area"] = _q(
        guarantee["values"].get("casing_area"), guarantee["units"].get("casing_area")
    )
    kwargs["surface_roughness"] = _q(
        guarantee["values"].get("surface_roughness"),
        guarantee["units"].get("surface_roughness"),
    )
    kwargs["speed"] = _q(values.get("speed"), units.get("speed"))
    return kwargs


def _section_results(back_to_back, sec: str, point_interpolated) -> dict:
    """Build the per-section results dict mirroring the Streamlit table."""
    test_points = getattr(back_to_back, f"test_points_{sec}")
    guarantee = getattr(back_to_back, f"guarantee_point_{sec}")
    flange_sp = getattr(back_to_back, f"points_flange_sp_{sec}")
    flange_t = getattr(back_to_back, f"points_flange_t_{sec}")
    rotor_sp = getattr(back_to_back, f"points_rotor_sp_{sec}")

    def _round(values):
        return [round(v, 5) for v in values]

    return {
        f"phi{_SUBSCRIPT_T}": _round(p.phi.m for p in test_points),
        f"phi{_SUBSCRIPT_T}/phi{_SUBSCRIPT_SP}": _round(
            p.phi.m / guarantee.phi.m for p in test_points
        ),
        "vi/vd": _round(p.volume_ratio.m for p in test_points),
        f"Mach{_SUBSCRIPT_T}": _round(p.mach.m for p in test_points),
        f"Re{_SUBSCRIPT_T}": _round(p.reynolds.m for p in test_points),
        f"pd{_SUPERSCRIPT_CONV} (bar)": _round(
            p.disch.p("bar").m for p in flange_sp
        ),
        f"Head{_SUPERSCRIPT_CONV} (kJ/kg)": _round(
            p.head.to("kJ/kg").m for p in flange_sp
        ),
        f"Q{_SUPERSCRIPT_CONV} (m3/h)": _round(
            p.flow_v.to("m³/h").m for p in flange_sp
        ),
        f"W{_SUPERSCRIPT_CONV} (kW)": _round(
            p.power_shaft.to("kW").m for p in rotor_sp
        ),
        f"Eff{_SUBSCRIPT_T}": _round(p.eff.m for p in flange_t),
        f"Eff{_SUPERSCRIPT_CONV}": _round(p.eff.m for p in flange_sp),
        "interpolated_flow_v_m3_h": round(
            point_interpolated.flow_v.to("m³/h").m, 5
        ),
        "interpolated_head_kJ_kg": round(
            point_interpolated.head.to("kJ/kg").m, 5
        ),
        "interpolated_eff": round(point_interpolated.eff.m, 5),
        "interpolated_discharge_pressure_bar": round(
            point_interpolated.disch.p("bar").m, 5
        ),
    }


def _generate_curve_plot(imp, point_interpolated, curve: str, *, show_points: bool):
    """Render a compressor curve figure for *curve* in ``CURVE_NAMES``."""
    plot_method = "disch.p" if curve == "discharge_pressure" else curve
    from ccp.config.utilities import r_getattr

    base = r_getattr(imp, f"{plot_method}_plot")(show_points=show_points)
    return r_getattr(point_interpolated, f"{plot_method}_plot")(
        fig=base, show_points=show_points
    )


def run_back_to_back(form_data: dict) -> dict:
    """Run the back-to-back computation and return a context dict.

    Parameters
    ----------
    form_data : dict
        Dict with the following keys:

        ``options`` : dict
            Cleaned :class:`SidebarOptionsForm` data.
        ``guarantee`` : dict with ``section_1`` and ``section_2`` entries,
            each shaped as ``{"values": {...}, "units": {...}, "fluid": {...}}``.
        ``test_points_first`` / ``test_points_second`` : list of dicts
            Same shape as the guarantee entries.
        ``calculate_speed`` : bool, optional
            If ``True``, call
            :meth:`BackToBack.calculate_speed_to_match_discharge_pressure`.

    Returns
    -------
    dict
        Context ready to be passed to the results template. Contains
        ``figures`` (mapping ``fig_<curve>_<sec>`` → Plotly figure objects),
        ``results_sec1`` / ``results_sec2`` tables, and ``speed_operational``.
    """
    options = form_data["options"]
    guarantee = form_data["guarantee"]
    test_points_first = form_data["test_points_first"]
    test_points_second = form_data["test_points_second"]

    try:
        ccp.config.POLYTROPIC_METHOD = POLYTROPIC_METHODS[
            options.get("polytropic_method", "Sandberg-Colby")
        ]
    except Exception:  # noqa: BLE001
        pass

    bearing_mechanical_losses = bool(options.get("bearing_mechanical_losses", True))
    casing_heat_loss = bool(options.get("casing_heat_loss", True))
    calculate_leakages = bool(options.get("calculate_leakages", True))
    seal_gas_flow = bool(options.get("seal_gas_flow", True))
    reynolds_correction = bool(options.get("reynolds_correction", True))
    show_points = bool(options.get("show_points", True))

    guarantee_point_sec1 = ccp.Point(
        **_guarantee_kwargs(
            guarantee["section_1"],
            bearing_mechanical_losses=bearing_mechanical_losses,
        )
    )
    guarantee_point_sec2 = ccp.Point(
        **_guarantee_kwargs(
            guarantee["section_2"],
            bearing_mechanical_losses=bearing_mechanical_losses,
        )
    )

    first_section_test_points = [
        PointFirstSection(
            **_test_point_kwargs(
                tp,
                guarantee["section_1"],
                casing_heat_loss=casing_heat_loss,
                calculate_leakages=calculate_leakages,
                seal_gas_flow=seal_gas_flow,
                bearing_mechanical_losses=bearing_mechanical_losses,
                is_first_section=True,
            )
        )
        for tp in test_points_first
        if tp.get("values", {}).get("flow")
    ]
    second_section_test_points = [
        PointSecondSection(
            **_test_point_kwargs(
                tp,
                guarantee["section_2"],
                casing_heat_loss=casing_heat_loss,
                calculate_leakages=calculate_leakages,
                seal_gas_flow=seal_gas_flow,
                bearing_mechanical_losses=bearing_mechanical_losses,
                is_first_section=False,
            )
        )
        for tp in test_points_second
        if tp.get("values", {}).get("flow")
    ]

    back_to_back = ccp_service.build_back_to_back(
        guarantee_point_sec1=guarantee_point_sec1,
        guarantee_point_sec2=guarantee_point_sec2,
        test_points_first=first_section_test_points,
        test_points_second=second_section_test_points,
        reynolds_correction=reynolds_correction,
        bearing_mechanical_losses=bearing_mechanical_losses,
    )

    if form_data.get("calculate_speed"):
        back_to_back = back_to_back.calculate_speed_to_match_discharge_pressure()

    figures: dict[str, Any] = {}
    results: dict[str, dict] = {}
    point_interpolated_sec1 = back_to_back.point_sec1(
        flow_v=back_to_back.guarantee_point_sec1.flow_v,
        speed=back_to_back.speed_operational,
    )
    point_interpolated_sec2 = back_to_back.point_sec2(
        flow_v=back_to_back.guarantee_point_sec2.flow_v,
        speed=back_to_back.speed_operational,
    )

    for sec, point_interpolated in (
        ("sec1", point_interpolated_sec1),
        ("sec2", point_interpolated_sec2),
    ):
        figures[f"fig_mach_{sec}"] = point_interpolated.plot_mach()
        figures[f"fig_reynolds_{sec}"] = point_interpolated.plot_reynolds()
        imp = getattr(back_to_back, f"imp_flange_sp_{sec}")
        for curve in CURVE_NAMES:
            figures[f"fig_{curve}_{sec}"] = _generate_curve_plot(
                imp, point_interpolated, curve, show_points=show_points
            )
        results[sec] = _section_results(back_to_back, sec, point_interpolated)

    return {
        "figures": figures,
        "results_sec1": results["sec1"],
        "results_sec2": results["sec2"],
        "speed_operational_rpm": float(back_to_back.speed_operational.to("rpm").m),
        "back_to_back": back_to_back,
    }
