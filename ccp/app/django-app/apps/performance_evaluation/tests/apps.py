"""Minimal ``AppConfig`` so the tests package can host a ``templatetags`` lib."""

from django.apps import AppConfig


class PerformanceEvaluationTestsConfig(AppConfig):
    name = "apps.performance_evaluation.tests"
    label = "performance_evaluation_tests"
