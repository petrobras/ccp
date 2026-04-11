"""Populate ``sys.modules`` with stub substitutes for missing cross-unit code.

Importing this module installs lightweight replacements for the public symbols
listed in the migration plan (Units 2, 3, 4). Real implementations replace the
stubs at merge time — the ``try/except ImportError`` pattern in ``services.py``
means this shim is only needed while running the page in isolation.

# STUB: replaced by Units 2-4 at merge time
"""

from __future__ import annotations

import importlib
import sys
import types


def _ensure(name: str, factory):
    """Install *factory()* into ``sys.modules`` under *name* if missing."""
    try:
        importlib.import_module(name)
        return
    except ModuleNotFoundError:
        sys.modules[name] = factory()


def _ccp_service_module() -> types.ModuleType:
    module = types.ModuleType("apps.core.services.ccp_service")

    def build_back_to_back(
        guarantee_point_sec1,
        guarantee_point_sec2,
        test_points_first,
        test_points_second,
        **opts,
    ):
        try:
            from ccp.compressor import BackToBack
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("ccp library required") from exc
        return BackToBack(
            guarantee_point_sec1=guarantee_point_sec1,
            guarantee_point_sec2=guarantee_point_sec2,
            test_points_sec1=list(test_points_first),
            test_points_sec2=list(test_points_second),
            reynolds_correction=opts.get("reynolds_correction", True),
            bearing_mechanical_losses=opts.get("bearing_mechanical_losses", True),
        )

    def build_point_1sec(**kwargs):
        import ccp

        return ccp.Point(**kwargs)

    def build_point_first_section(**kwargs):
        from ccp.compressor import PointFirstSection

        return PointFirstSection(**kwargs)

    def build_point_second_section(**kwargs):
        from ccp.compressor import PointSecondSection

        return PointSecondSection(**kwargs)

    def build_gas_state(composition, p, T):
        import ccp

        return ccp.State(p=p, T=T, fluid=dict(composition))

    module.build_back_to_back = build_back_to_back
    module.build_point_1sec = build_point_1sec
    module.build_point_first_section = build_point_first_section
    module.build_point_second_section = build_point_second_section
    module.build_gas_state = build_gas_state
    return module


def _gas_composition_module() -> types.ModuleType:
    module = types.ModuleType("apps.core.services.gas_composition")
    module.FLUID_LIST = [
        "methane",
        "ethane",
        "propane",
        "n-butane",
        "i-butane",
        "nitrogen",
        "carbon dioxide",
        "hydrogen sulfide",
        "water",
    ]

    def default_composition() -> dict:
        return {"methane": 1.0}

    def get_gas_composition(gas_name, gas_compositions_table, default_components):
        if not gas_compositions_table:
            return {"methane": 1.0}
        for row in gas_compositions_table:
            if row.get("name") == gas_name:
                return {
                    k: float(v)
                    for k, v in row.items()
                    if k != "name" and v not in (None, "", 0, 0.0)
                }
        return {"methane": 1.0}

    module.default_composition = default_composition
    module.get_gas_composition = get_gas_composition
    return module


def _storage_importer_module() -> types.ModuleType:
    module = types.ModuleType("apps.core.storage.ccp_file_importer")

    def load_ccp_file(fp) -> dict:
        import io
        import json
        import zipfile

        state: dict = {}
        data = fp.read() if hasattr(fp, "read") else fp
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    state.update(json.loads(zf.read(name)))
                elif name.endswith(".png"):
                    state[name.split(".")[0]] = zf.read(name)
        return state

    module.load_ccp_file = load_ccp_file
    return module


def _storage_exporter_module() -> types.ModuleType:
    module = types.ModuleType("apps.core.storage.ccp_file_exporter")

    def export_ccp_file(state: dict) -> bytes:
        import io
        import json
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            serialisable = {
                k: v
                for k, v in state.items()
                if isinstance(v, (str, int, float, bool, list, dict, type(None)))
            }
            zf.writestr("session_state.json", json.dumps(serialisable, default=str))
        return buf.getvalue()

    module.export_ccp_file = export_ccp_file
    return module


def _session_store_module() -> types.ModuleType:
    module = types.ModuleType("apps.core.session_store")
    _cache: dict[str, dict] = {}

    def get_session(session_id: str) -> dict:
        return _cache.get(session_id, {})

    def set_session(session_id: str, state: dict) -> None:
        _cache[session_id] = dict(state)

    def clear_session(session_id: str) -> None:
        _cache.pop(session_id, None)

    module.get_session = get_session
    module.set_session = set_session
    module.clear_session = clear_session
    return module


def _models_module() -> types.ModuleType:
    module = types.ModuleType("apps.core.models")

    class Session:  # noqa: D401
        """Minimal in-memory Session placeholder."""

        def __init__(self, name="", app_type="back_to_back", state=None):
            self.name = name
            self.app_type = app_type
            self.state = state or {}

    module.Session = Session
    return module


def _templatetags_module() -> types.ModuleType:
    from django import template
    from django.utils.safestring import mark_safe

    module = types.ModuleType("apps.core.templatetags.ccp_tags")
    register = template.Library()

    @register.simple_tag
    def plotly_figure(fig, div_id=None):
        if fig is None:
            return ""
        try:
            import plotly.io as pio

            return mark_safe(
                pio.to_html(fig, full_html=False, include_plotlyjs=False)
            )
        except Exception:
            return ""

    @register.inclusion_tag("core/partials/expander.html", takes_context=False)
    def expander(title, body_id, expanded=False):
        return {"title": title, "body_id": body_id, "expanded": expanded}

    @register.inclusion_tag("core/partials/parameter_row.html")
    def parameter_row(key, value, unit_choices):
        return {"key": key, "value": value, "unit_choices": unit_choices}

    module.register = register
    module.plotly_figure = plotly_figure
    module.expander = expander
    module.parameter_row = parameter_row
    return module


def install() -> None:
    """Install all stub modules required by the back-to-back app."""
    # Pre-register ccp_service BEFORE ``apps.core.services/__init__.py`` is
    # imported: its package ``__init__`` re-exports ``ccp_service`` eagerly,
    # so we must put our stub into ``sys.modules`` first.
    if "apps.core.services.ccp_service" not in sys.modules:
        sys.modules["apps.core.services.ccp_service"] = _ccp_service_module()
    _ensure("apps.core", lambda: types.ModuleType("apps.core"))
    _ensure("apps.core.services", lambda: types.ModuleType("apps.core.services"))
    _ensure("apps.core.services.ccp_service", _ccp_service_module)
    _ensure("apps.core.services.gas_composition", _gas_composition_module)
    _ensure("apps.core.storage", lambda: types.ModuleType("apps.core.storage"))
    _ensure("apps.core.storage.ccp_file_importer", _storage_importer_module)
    _ensure("apps.core.storage.ccp_file_exporter", _storage_exporter_module)
    _ensure("apps.core.session_store", _session_store_module)
    _ensure("apps.core.models", _models_module)
    _ensure(
        "apps.core.templatetags",
        lambda: types.ModuleType("apps.core.templatetags"),
    )
    _ensure("apps.core.templatetags.ccp_tags", _templatetags_module)
