# STUB: replaced by Unit 2 (apps.core.services.gas_composition) at merge time.
"""Minimal fluid list + default composition for offline tests."""

FLUID_LIST = [
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


def default_composition():
    """Return a default methane-dominant composition."""
    return {"methane": 0.95, "ethane": 0.03, "nitrogen": 0.02}
