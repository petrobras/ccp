from django.apps import AppConfig


class PerformanceTestConfig(AppConfig):
    name = "ccp_web.performance_test"
    label = "ccp_performance_test"
    verbose_name = "Performance test"

    def ready(self):
        from . import jobs  # noqa: F401  (registers the job handlers)
