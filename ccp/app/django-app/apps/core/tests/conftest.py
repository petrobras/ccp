"""Pytest bootstrap for Unit 12 tests.

Ensures the Unit 12 local scaffold settings are loaded before Django
imports are executed. Unit 1 will replace these settings at merge time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django


def pytest_configure(config):
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ccp_web.settings")
    django.setup()
