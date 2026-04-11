"""Pytest configuration for the back-to-back app.

Boots Django with the local stub settings module so the tests can run in
isolation (Unit 1's ``ccp_web`` package may not exist yet in this worktree).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

DJANGO_APP_ROOT = Path(__file__).resolve().parents[3]
if str(DJANGO_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(DJANGO_APP_ROOT))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "apps.back_to_back._stubs.settings"
)

import django  # noqa: E402

django.setup()
