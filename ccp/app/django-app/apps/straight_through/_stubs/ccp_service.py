# STUB: replaced by Unit 2 at merge time
"""Fallback wrapper around the ``ccp`` compressor helpers.

Only used when :mod:`apps.core.services.ccp_service` is unavailable (i.e. the
other units have not yet been merged into the worktree). It forwards every
call directly to the ``ccp`` library.
"""

from __future__ import annotations

from typing import Any

import ccp
from ccp.compressor import Point1Sec, StraightThrough


Q_ = ccp.Q_


def build_gas_state(composition: dict, p: Any, T: Any) -> ccp.State:
    """Instantiate a :class:`ccp.State` from a composition dict."""
    return ccp.State(p=p, T=T, fluid=composition)


def build_point_1sec(**kwargs: Any) -> Point1Sec:
    """Construct a :class:`ccp.compressor.Point1Sec` from raw kwargs."""
    return Point1Sec(**kwargs)


def build_guarantee_point(**kwargs: Any) -> ccp.Point:
    """Construct the guarantee :class:`ccp.Point`."""
    return ccp.Point(**kwargs)


def build_straight_through(
    guarantee_point: ccp.Point,
    test_points: list[Point1Sec],
    *,
    reynolds_correction: bool = True,
    bearing_mechanical_losses: bool = False,
    calculate_speed: bool = False,
    **_: Any,
) -> StraightThrough:
    """Assemble a :class:`ccp.compressor.StraightThrough` instance."""
    straight = StraightThrough(
        guarantee_point=guarantee_point,
        test_points=test_points,
        reynolds_correction=reynolds_correction,
        bearing_mechanical_losses=bearing_mechanical_losses,
    )
    if calculate_speed:
        straight = straight.calculate_speed_to_match_discharge_pressure()
    return straight
