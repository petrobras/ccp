from django.apps import AppConfig


class DigitizerConfig(AppConfig):
    name = "ccp_web.digitizer"
    label = "ccp_digitizer"
    verbose_name = "Curves digitizer"

    def ready(self):
        from . import jobs  # noqa: F401  (registers the job handlers)
