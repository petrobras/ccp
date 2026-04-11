# STUB: replaced by Unit 2 at merge time
"""Fallback gas-composition helpers."""

from __future__ import annotations

FLUID_LIST: list[str] = [
    "methane",
    "ethane",
    "propane",
    "n-butane",
    "i-butane",
    "n-pentane",
    "i-pentane",
    "n-hexane",
    "nitrogen",
    "carbon dioxide",
    "hydrogen sulfide",
    "water",
]


def default_composition() -> dict[str, float]:
    """Return a methane-dominant default composition."""
    return {"methane": 1.0}
