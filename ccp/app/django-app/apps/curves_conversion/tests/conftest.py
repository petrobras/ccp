"""Pytest bootstrap for the curves conversion unit tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

DJANGO_APP_ROOT = Path(__file__).resolve().parents[3]
if str(DJANGO_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(DJANGO_APP_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.curves_conversion.tests.settings")

import django  # noqa: E402

django.setup()
