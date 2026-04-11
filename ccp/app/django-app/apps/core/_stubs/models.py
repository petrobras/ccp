"""Models stub.

# STUB: replaced by Unit 3 (apps.core.models) at merge time with a
# MongoEngine Document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    """Lightweight in-memory stand-in for the real MongoEngine document."""

    name: str = ""
    app_type: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    ccp_version: str = ""
