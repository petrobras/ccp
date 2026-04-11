"""AppConfig for the performance evaluation Django app."""

from django.apps import AppConfig


class PerformanceEvaluationConfig(AppConfig):
    """Django AppConfig for performance_evaluation."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.performance_evaluation"
    label = "performance_evaluation"
    verbose_name = "Performance Evaluation"
