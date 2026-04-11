"""AppConfig wiring project-level side effects (Plotly theme)."""

from django.apps import AppConfig


class PlotlyConfig(AppConfig):
    """Register the ``ccp`` Plotly template on Django startup."""

    name = "ccp_web"
    label = "ccp_web"
    verbose_name = "ccp web"

    def ready(self) -> None:
        from . import plotly_config  # noqa: F401
