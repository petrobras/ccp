# STUB: replaced by Unit 2 at merge time
"""Fallback :func:`build_evaluation` wrapper.

Only used when :mod:`apps.core.services.ccp_service` is unavailable.
"""

from __future__ import annotations

from typing import Any

import ccp


def build_evaluation(**kwargs: Any) -> ccp.Evaluation:
    """Construct a :class:`ccp.Evaluation` directly from kwargs."""
    return ccp.Evaluation(**kwargs)
