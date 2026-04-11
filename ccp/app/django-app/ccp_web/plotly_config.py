"""Register the ``ccp`` Plotly template for server-side figure rendering.

Importing :mod:`ccp.plotly_theme` triggers registration of the custom
template through ``plotly.io.templates``. This module is imported from
:class:`ccp_web.apps.PlotlyConfig.ready` so Django startup guarantees the
template is available whenever views render figures.
"""

from __future__ import annotations

try:
    import ccp.plotly_theme  # noqa: F401
except Exception:
    pass
