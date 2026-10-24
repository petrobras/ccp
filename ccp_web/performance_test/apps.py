from django.apps import AppConfig


class PerformanceTestConfig(AppConfig):
    name = "ccp_web.performance_test"
    label = "ccp_performance_test"
    verbose_name = "Performance test"

    def ready(self):
        import functools

        from ccp_web.core.state import register_post_save_hook
        from ccp_web.services import performance_test as pt

        from . import jobs  # noqa: F401  (registers the job handlers)

        # Switching a section's flow method keeps the measured flows aside
        # (and restores them), after a form save and after an agent write.
        for app_type in ("straight_through", "back_to_back"):
            register_post_save_hook(
                [app_type], functools.partial(pt.switch_flow_method, app_type)
            )
