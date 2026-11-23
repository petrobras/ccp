import sys
import types

POLYTROPIC_METHOD = "sandberg_colby"
EOS = "REFPROP"  # also "HEOS", "PR", "SRK", "ideal" or "ideal:k=<k>" (see ccp.State)

# Phase imposed on states built without an explicit phase, after a one-off
# unconstrained flash confirms the state is single phase there (see
# ccp.State). The states derived from it by the point solvers (discharge,
# isentropic and dummy states) inherit the phase, so their flashes skip the
# phase-stability analysis that dominates the cost of a flash calculation.
# None restores the legacy behaviour (every flash unconstrained). A state
# built with phase=False opts out individually.
DEFAULT_PHASE = "gas"
# Opt-in diagnostic: verify every discharge state resolved under an imposed
# phase with one unconstrained flash (a phase-stability analysis, 2 to
# 100 ms per state for multi-component mixtures on REFPROP, i.e. up to ten
# times the point solve itself). A mismatch (metastable root inside the
# phase envelope) re-solves the point unconstrained and emits a
# ccp.point.PhaseWarning. Off by default: a compression from a single-phase
# suction moves away from the dew line.
PHASE_CHECK = False

# Multiprocessing controls, read at pool-creation time (see ccp/parallel.py).
# The CCP_PARALLEL and CCP_POOL_SIZE environment variables take precedence.
PARALLEL = True  # set to False to run every ccp calculation serially
POOL_SIZE = None  # worker processes per pool; None means one per CPU

# Ambient pressure in Pa (1 atm), the reference of the gauge units (barg, psig,
# kPag and MPag). Change it with ccp.set_ambient_pressure or, for a block of
# code, with ccp.ambient_pressure.
AMBIENT_PRESSURE = 101325.0


class _Config(types.ModuleType):
    """Config module that keeps the gauge units consistent with AMBIENT_PRESSURE."""

    def __setattr__(self, name, value):
        if name == "AMBIENT_PRESSURE":
            from .units import set_ambient_pressure

            set_ambient_pressure(value)
        else:
            super().__setattr__(name, value)


sys.modules[__name__].__class__ = _Config
