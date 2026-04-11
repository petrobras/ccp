# STUB: replaced by Unit 3 at merge time.
"""Minimal fallback for :class:`apps.core.models.Session`."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Session:
    """Lightweight placeholder matching the MongoEngine ``Session`` document."""

    name: str = ""
    app_type: str = "performance_evaluation"
    state: dict = field(default_factory=dict)
    ccp_version: str = ""
