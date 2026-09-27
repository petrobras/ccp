from django.apps import AppConfig


class CurvesConfig(AppConfig):
    name = "ccp_web.curves"
    label = "ccp_curves"
    verbose_name = "Curves"

    def ready(self):
        from . import jobs  # noqa: F401  (registers the job handlers)
