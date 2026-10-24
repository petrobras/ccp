"""Agent adapter of the straight-through and back-to-back pages.

See ``ccp_web.agent.adapters`` for the interface. ``start`` is the page's
Calculate button (``views.start_calculation``); results and figures come from
the stored compressor TOML through the same services as the results view.
"""

from ccp_web.agent.adapters import json_safe
from ccp_web.core.models import Job
from ccp_web.services import performance_test as pt
from ccp_web.services import units

from .views import load_compressor, start_calculation

APP_TYPES = ("straight_through", "back_to_back")
PARAMS = {
    "calculate_speed": (
        "bool, default false: find the speed that matches the guarantee "
        "discharge pressure (the page's 'Calculate speed' option)"
    ),
}
FIGURES = [
    ("mach", "Mach"),
    ("reynolds", "Reynolds"),
    ("head", "Head"),
    ("eff", "Efficiency"),
    ("discharge_pressure", "Discharge pressure"),
    ("power", "Gas power"),
]
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def _flag(name, value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in _TRUE | _FALSE:
        return value.strip().lower() in _TRUE
    raise ValueError(f"{name}: expected true or false, got {value!r}")


def start(case, params):
    """Start the PTC 10 calculation; ``params``: ``{calculate_speed: bool}``."""
    params = dict(params or {})
    unknown = sorted(set(params) - set(PARAMS))
    if unknown:
        raise ValueError(f"unknown params {unknown}; expected {sorted(PARAMS)}")
    return start_calculation(
        case, calculate_speed=_flag("calculate_speed", params.get("calculate_speed"))
    )


def has_results(case):
    return case.artifact(case.app_type) is not None


def _last_job(case):
    return Job.objects.filter(case=case, kind="calculate").order_by("-created").first()


def _section_id(sec):
    return sec.sec or "st"


def results(case):
    """The results tables (one per section), speed and the PTC 10 checks.

    Row values are keyed by column; the column names carry the units. The
    ratio columns (``FRACTION_COLUMNS``) are fractions: 1.0 is 100 %.
    """
    compressor, artifact = load_compressor(case)
    job = _last_job(case)
    if compressor is None:
        reason = "not calculated yet: POST calculate"
        if job is not None and job.status == Job.FAILED:
            reason = f"the last calculation failed: {job.error}"
        out = {"available": False, "reason": reason}
        if job is not None and job.status == Job.FAILED:
            out["errors"] = (job.result or {}).get("errors") or {}
        return out
    with units.state_context(case.state):
        tables = pt.results(case.app_type, compressor, case.state)
        speed = compressor.speed_operational.to("rpm").m
    sections = []
    for sec, table in zip(pt.sections(case.app_type), tables):
        sections.append(
            {
                "id": _section_id(sec),
                "title": table["title"],
                "columns": table["columns"],
                "rows": [
                    {
                        "label": row["label"],
                        "values": dict(zip(table["columns"], row["values"])),
                    }
                    for row in table["rows"]
                ],
                "checks": table["checks"],
                "all_ok": all(c["ok"] for c in table["checks"]),
            }
        )
    out = {
        "available": True,
        "app_type": case.app_type,
        "speed_rpm": speed,
        "all_ok": all(c["ok"] for s in sections for c in s["checks"]),
        "sections": sections,
        "fraction_columns": sorted(pt.PERCENT_COLUMNS),
        "calculated": artifact.created,
        "inputs_saved_after_calculation": case.updated > artifact.created,
    }
    if job is not None:
        out["job"] = {
            "id": job.pk,
            "status": job.status,
            "warnings": list(job.warnings or []),
            "params": job.params,
        }
    return json_safe(out)


def figures(case):
    if not has_results(case):
        return []
    items = []
    for sec in pt.sections(case.app_type):
        for name, title in FIGURES:
            items.append(
                {
                    "id": sec.curve_prefix(name),
                    "title": title if sec.name is None else f"{title} ({sec.title})",
                    "section": _section_id(sec),
                }
            )
    return items


def figure(case, figure_id):
    """One results figure, without the page's curve image overlay."""
    for sec in pt.sections(case.app_type):
        for name, _ in FIGURES:
            if sec.curve_prefix(name) == figure_id:
                compressor, _ = load_compressor(case)
                if compressor is None:
                    raise KeyError(figure_id)
                with units.state_context(case.state):
                    pi = pt.interpolated_point(compressor, sec)
                    figs, _ = pt.figures(
                        case.app_type,
                        compressor,
                        case.state,
                        sec,
                        point_interpolated=pi,
                    )
                return figs[name]
    raise KeyError(figure_id)
