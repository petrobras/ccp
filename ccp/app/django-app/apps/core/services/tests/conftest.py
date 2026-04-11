"""Pytest fixtures for the services test suite.

Adds the ``django-app/`` root to ``sys.path`` so tests can import
``apps.core.services`` without a Django project being wired up yet.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
