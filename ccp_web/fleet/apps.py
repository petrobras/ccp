from django.apps import AppConfig


class FleetConfig(AppConfig):
    name = "ccp_web.fleet"
    label = "ccp_fleet"
    verbose_name = "Fleet analysis"

    def ready(self):
        from . import jobs  # noqa: F401  (registers the job handlers)
