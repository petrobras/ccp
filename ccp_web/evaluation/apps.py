from django.apps import AppConfig


class EvaluationConfig(AppConfig):
    name = "ccp_web.evaluation"
    label = "ccp_evaluation"
    verbose_name = "Evaluation"

    def ready(self):
        from . import jobs  # noqa: F401  (registers the job handlers)
