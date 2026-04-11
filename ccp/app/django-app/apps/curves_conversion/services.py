"""Service layer for the curves conversion page.

All compressor math delegates to the ``ccp`` Python library through
:mod:`apps.core.services.ccp_service` (with a local stub fallback). Plotly
figures are rendered to HTML fragments that the templates embed directly.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ccp
import plotly.io as pio
from django.core.cache import cache

try:
    from apps.core.services import ccp_service
except ImportError:  # pragma: no cover - stub fallback
    from apps.curves_conversion._stubs import ccp_service  # type: ignore

Q_ = ccp.Q_

FLOW_V_UNITS = {"m³/h", "m³/min", "m³/s"}


@dataclass
class CurveFile:
    """In-memory representation of an uploaded Engauge CSV."""

    name: str
    content: bytes


def extract_curve_name(filename: str) -> str:
    """Strip a known curve suffix from *filename*.

    Parameters
    ----------
    filename : str
        CSV filename, typically ``<curve>-head.csv`` or ``<curve>-eff.csv``.

    Returns
    -------
    str
        The base curve name with suffix and extension removed.
    """
    name = filename.rsplit(".", 1)[0]
    suffixes = [
        "head",
        "eff",
        "power",
        "power_shaft",
        "pressure_ratio",
        "disch_T",
    ]
    for suffix in suffixes:
        marker = f"-{suffix}"
        if name.endswith(marker):
            return name[: -len(marker)]
    return name


def resolve_flow_v_unit(flow_unit: str) -> str:
    """Return a volumetric flow unit, defaulting to ``m³/h`` for mass-flow inputs."""
    return flow_unit if flow_unit in FLOW_V_UNITS else "m³/h"


def figure_to_html(fig) -> str:
    """Render a Plotly figure to an embeddable HTML fragment.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        Figure produced by ``ccp``'s plotting helpers.

    Returns
    -------
    str
        HTML fragment without ``<html>`` wrapping; Plotly.js is expected to be
        loaded once by ``base.html``.
    """
    try:
        fig.update_layout(template="ccp")
    except Exception:  # pragma: no cover - template registration is optional
        pass
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def _hash_key(prefix: str, payload: dict[str, Any]) -> str:
    """Compute a stable cache key for *prefix* and *payload*."""
    digest = hashlib.sha1(
        repr(sorted(payload.items())).encode("utf-8"), usedforsecurity=False
    ).hexdigest()
    return f"curves_conversion:{prefix}:{digest}"


def load_original_impeller(
    *,
    curve_files: list[CurveFile],
    suction_pressure: float,
    suction_pressure_unit: str,
    suction_temperature: float,
    suction_temperature_unit: str,
    gas_composition: dict,
    flow_unit: str,
    head_unit: str,
    power_unit: str,
    disch_p_unit: str,
    disch_T_unit: str,
    speed_unit: str,
) -> ccp.Impeller:
    """Load a :class:`ccp.Impeller` from uploaded Engauge CSVs.

    Parameters
    ----------
    curve_files : list of CurveFile
        Uploaded CSVs (at least one).
    suction_pressure, suction_temperature : float
        Suction state magnitudes.
    suction_pressure_unit, suction_temperature_unit : str
        Units for the suction state.
    gas_composition : dict
        Component-to-molar-fraction mapping for the suction gas.
    flow_unit, head_unit, power_unit, disch_p_unit, disch_T_unit, speed_unit : str
        Units used inside the CSV files.

    Returns
    -------
    ccp.Impeller
        Impeller loaded from the provided curves.
    """
    if not curve_files:
        raise ValueError("No curve files supplied.")

    suction_state = ccp_service.build_gas_state(
        gas_composition,
        Q_(suction_pressure, suction_pressure_unit),
        Q_(suction_temperature, suction_temperature_unit),
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="ccp_curves_"))
    try:
        for curve in curve_files:
            (temp_dir / curve.name).write_bytes(curve.content)
        curve_name = extract_curve_name(curve_files[0].name)
        return ccp_service.load_impeller_from_engauge_csv(
            suction_state=suction_state,
            curve_name=curve_name,
            curve_path=temp_dir,
            flow_units=flow_unit,
            disch_p_units=disch_p_unit,
            disch_T_units=disch_T_unit,
            head_units=head_unit,
            power_units=power_unit,
            speed_units=speed_unit,
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def convert_impeller(
    *,
    original_impeller: ccp.Impeller,
    new_suction_pressure: float,
    new_suction_pressure_unit: str,
    new_suction_temperature: float,
    new_suction_temperature_unit: str,
    new_gas_composition: dict,
    find_method: str = "speed",
    speed_option: str = "same",
) -> ccp.Impeller:
    """Convert *original_impeller* to new suction conditions.

    Parameters
    ----------
    original_impeller : ccp.Impeller
        Impeller loaded from the original curves.
    new_suction_pressure, new_suction_temperature : float
        Target suction state magnitudes.
    new_suction_pressure_unit, new_suction_temperature_unit : str
        Units for the target suction state.
    new_gas_composition : dict
        Component-to-molar-fraction mapping for the target gas.
    find_method : str, optional
        Passed to :meth:`ccp.Impeller.convert_from` as ``find``.
    speed_option : str, optional
        ``"same"`` keeps the original speed, ``"calculate"`` lets ``ccp`` pick.

    Returns
    -------
    ccp.Impeller
        The converted impeller.
    """
    suction_state = ccp_service.build_gas_state(
        new_gas_composition,
        Q_(new_suction_pressure, new_suction_pressure_unit),
        Q_(new_suction_temperature, new_suction_temperature_unit),
    )
    speed = "same" if speed_option == "same" else None
    return ccp_service.convert_impeller(
        original_impeller=original_impeller,
        suction_state=suction_state,
        find=find_method,
        speed=speed,
    )


def generate_figures(
    impeller: ccp.Impeller,
    *,
    flow: float,
    flow_v_unit: str,
    speed: float,
    speed_unit: str,
    head_unit: str,
    power_unit: str,
    disch_T_unit: str,
    disch_p_unit: str,
) -> dict[str, Any]:
    """Build the five Plotly figures displayed on the page.

    Uses the Django cache to memoise figure HTML keyed on the impeller identity
    plus the plot parameters. Cached values live for one hour.

    Parameters
    ----------
    impeller : ccp.Impeller
        Impeller to plot.
    flow, speed : float
        Operational point magnitudes.
    flow_v_unit, speed_unit, head_unit, power_unit, disch_T_unit, disch_p_unit : str
        Display units.

    Returns
    -------
    dict
        ``{"head", "power", "disch_T", "eff", "disch_p"}`` HTML fragments and a
        ``"project_point"`` summary dict.
    """
    impeller_hash = hash(impeller)
    payload = {
        "impeller_hash": impeller_hash,
        "flow": flow,
        "flow_v_unit": flow_v_unit,
        "speed": speed,
        "speed_unit": speed_unit,
        "head_unit": head_unit,
        "power_unit": power_unit,
        "disch_T_unit": disch_T_unit,
        "disch_p_unit": disch_p_unit,
    }
    key = _hash_key("figures", payload)

    def _compute() -> dict[str, Any]:
        flow_q = Q_(flow, flow_v_unit)
        speed_q = Q_(speed, speed_unit)
        head_fig = impeller.head_plot(
            flow_v_units=flow_v_unit,
            head_units=head_unit,
            flow_v=flow_q,
            speed=speed_q,
        )
        power_fig = impeller.power_plot(
            flow_v_units=flow_v_unit,
            power_units=power_unit,
            flow_v=flow_q,
            speed=speed_q,
        )
        disch_T_fig = impeller.disch.T_plot(
            flow_v_units=flow_v_unit,
            temperature_units=disch_T_unit,
            flow_v=flow_q,
            speed=speed_q,
        )
        eff_fig = impeller.eff_plot(
            flow_v_units=flow_v_unit,
            flow_v=flow_q,
            speed=speed_q,
        )
        disch_p_fig = impeller.disch.p_plot(
            flow_v_units=flow_v_unit,
            p_units=disch_p_unit,
            flow_v=flow_q,
            speed=speed_q,
        )
        project_point = impeller.point(flow_v=flow_q, speed=speed_q)
        return {
            "head": figure_to_html(head_fig),
            "power": figure_to_html(power_fig),
            "disch_T": figure_to_html(disch_T_fig),
            "eff": figure_to_html(eff_fig),
            "disch_p": figure_to_html(disch_p_fig),
            "project_point": _describe_point(
                project_point,
                flow_v_unit=flow_v_unit,
                speed_unit=speed_unit,
                head_unit=head_unit,
                power_unit=power_unit,
                disch_T_unit=disch_T_unit,
                disch_p_unit=disch_p_unit,
            ),
        }

    return cache.get_or_set(key, _compute, timeout=3600)


def _describe_point(
    point,
    *,
    flow_v_unit: str,
    speed_unit: str,
    head_unit: str,
    power_unit: str,
    disch_T_unit: str,
    disch_p_unit: str,
) -> dict[str, Any]:
    """Return a serialisable summary of *point* in the requested units."""
    return {
        "speed": round(point.speed.to("rpm").m, 0),
        "speed_unit": speed_unit,
        "flow": round(point.flow_v.to(flow_v_unit).m, 2),
        "flow_unit": flow_v_unit,
        "head": round(point.head.to(head_unit).m, 2),
        "head_unit": head_unit,
        "eff": round(point.eff.m, 4),
        "power": round(point.power.to(power_unit).m, 2),
        "power_unit": power_unit,
        "suc_p": round(point.suc.p(disch_p_unit).m, 2),
        "suc_T": round(point.suc.T(disch_T_unit).m, 2),
        "disch_p": round(point.disch.p(disch_p_unit).m, 2),
        "disch_T": round(point.disch.T(disch_T_unit).m, 2),
        "disch_p_unit": disch_p_unit,
        "disch_T_unit": disch_T_unit,
    }


def run_conversion(
    *,
    original_data: dict,
    converted_data: dict,
    curves_files: list[CurveFile],
    conversion_params: dict,
) -> dict[str, Any]:
    """Full pipeline: load original impeller, convert it, and render figures.

    Parameters
    ----------
    original_data : dict
        Original suction conditions (pressure, temperature, units, gas).
    converted_data : dict
        Target suction conditions (pressure, temperature, units, gas).
    curves_files : list of CurveFile
        Uploaded Engauge CSVs.
    conversion_params : dict
        Dictionary of conversion + plot parameters (units, operational point,
        ``find_method``, ``speed_option``).

    Returns
    -------
    dict
        ``{"original_impeller", "converted_impeller", "original_figures",
        "converted_figures"}``.
    """
    original_impeller = load_original_impeller(
        curve_files=curves_files,
        suction_pressure=original_data["pressure"],
        suction_pressure_unit=original_data["pressure_unit"],
        suction_temperature=original_data["temperature"],
        suction_temperature_unit=original_data["temperature_unit"],
        gas_composition=original_data.get("gas_composition", {"methane": 1.0}),
        flow_unit=conversion_params["loaded_flow_unit"],
        head_unit=conversion_params["loaded_head_unit"],
        power_unit=conversion_params["loaded_power_unit"],
        disch_p_unit=conversion_params["loaded_disch_p_unit"],
        disch_T_unit=conversion_params["loaded_disch_T_unit"],
        speed_unit=conversion_params["loaded_speed_unit"],
    )
    converted_impeller = convert_impeller(
        original_impeller=original_impeller,
        new_suction_pressure=converted_data["pressure"],
        new_suction_pressure_unit=converted_data["pressure_unit"],
        new_suction_temperature=converted_data["temperature"],
        new_suction_temperature_unit=converted_data["temperature_unit"],
        new_gas_composition=converted_data.get("gas_composition", {"methane": 1.0}),
        find_method=conversion_params.get("find_method", "speed"),
        speed_option=conversion_params.get("speed_option", "same"),
    )

    plot_flow_v_unit = resolve_flow_v_unit(conversion_params["plot_flow_unit"])

    original_flow = conversion_params.get("operational_flow") or (
        original_impeller.points[0].flow_v.to(plot_flow_v_unit).m
    )
    original_speed = conversion_params.get("operational_speed") or (
        original_impeller.points[0].speed.to(conversion_params["plot_speed_unit"]).m
    )
    converted_flow = conversion_params.get("converted_flow") or (
        converted_impeller.points[0].flow_v.to(plot_flow_v_unit).m
    )
    converted_speed = conversion_params.get("converted_speed") or (
        converted_impeller.points[0].speed.to(conversion_params["plot_speed_unit"]).m
    )

    plot_kwargs = dict(
        flow_v_unit=plot_flow_v_unit,
        speed_unit=conversion_params["plot_speed_unit"],
        head_unit=conversion_params["plot_head_unit"],
        power_unit=conversion_params["plot_power_unit"],
        disch_T_unit=conversion_params["plot_disch_T_unit"],
        disch_p_unit=conversion_params["plot_disch_p_unit"],
    )
    original_figures = generate_figures(
        original_impeller, flow=original_flow, speed=original_speed, **plot_kwargs
    )
    converted_figures = generate_figures(
        converted_impeller, flow=converted_flow, speed=converted_speed, **plot_kwargs
    )

    return {
        "original_impeller": original_impeller,
        "converted_impeller": converted_impeller,
        "original_figures": original_figures,
        "converted_figures": converted_figures,
    }
