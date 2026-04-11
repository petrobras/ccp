"""Pytest bootstrap: configure Django settings before tests import modules."""

import os
import sys
from pathlib import Path

DJANGO_APP_DIR = Path(__file__).resolve().parents[3]
if str(DJANGO_APP_DIR) not in sys.path:
    sys.path.insert(0, str(DJANGO_APP_DIR))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "apps.performance_evaluation.tests._test_settings",
)

import django  # noqa: E402

django.setup()
