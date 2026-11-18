"""Cone flow meter (ISO 5167-5)."""

import warnings
from copy import copy

import numpy as np

from ccp import Q_
from ccp.config.units import check_units

__all__ = ["FlowCone", "FlowMeterWarning"]

# ISO 5167-5:2022: discharge coefficient of an uncalibrated cone meter
# (relative expanded uncertainty 5 %, k = 2) and the limits of use given for it
C_ISO = 0.82
D_LIMITS = (Q_(50, "mm"), Q_(500, "mm"))
BETA_LIMITS = (0.45, 0.75)
REYNOLDS_LIMITS = (8e4, 1.2e7)
# lowest p2/p1 of the expansibility factor equation
PRESSURE_RATIO_MIN = 0.75


class FlowMeterWarning(UserWarning):
    """A flow meter reading lies outside the limits of its standard.

    Emitted by :class:`ccp.FlowCone` when the geometry or the Reynolds number
    is outside the limits of the ISO 5167-5 discharge coefficient, when the
    Reynolds number is outside the range of a calibration table, and when the
    pressure ratio is below the limit of the expansibility factor equation.
    Silence it with
    ``warnings.filterwarnings("ignore", category=ccp.fc.FlowMeterWarning)``.
    """


class FlowCone:
    """Cone (V-cone) differential pressure flow meter (ISO 5167-5).

    The mass flow is calculated from the differential pressure between the
    upstream wall tapping and the tapping at the back face of the cone
    (ISO 5167-5:2022, Formula (1)):

    .. math::

        q_m = \\frac{C}{\\sqrt{1 - \\beta^4}} \\, \\varepsilon \\,
        \\frac{\\pi}{4} (D \\beta)^2 \\sqrt{2 \\Delta p \\rho_1}

    with :math:`\\beta = \\sqrt{1 - d_c^2 / D^2}` and the expansibility
    factor :math:`\\varepsilon = 1 - (0.649 + 0.696 \\beta^4)
    \\Delta p / (\\kappa p_1)`, where :math:`\\kappa` is the isentropic
    exponent at the upstream state.

    Without a calibration, the ISO 5167-5 discharge coefficient C = 0.82 is
    used. Its relative expanded uncertainty is 5 % (k = 2), and the standard
    only allows it for 50 mm <= D <= 500 mm, 0.45 <= beta <= 0.75 and
    8e4 <= ReD <= 1.2e7. A :class:`ccp.fc.FlowMeterWarning` is emitted
    outside these limits. Meters with beta > 0.75 must be calibrated. With a
    calibrated C these limits are not checked.

    Parameters
    ----------
    state : ccp.State
        State of the fluid at the upstream tapping (see ``state_upstream``).
    delta_p : float, pint.Quantity
        Differential pressure between the upstream tapping and the tapping
        at the back of the cone (Pa).
    D : float, pint.Quantity
        Pipe internal diameter at the meter (m). Use the measured internal
        diameter, not the nominal pipe size. As in ISO 5167-5, D and the cone
        diameter are the values at working conditions.
    d : float, pint.Quantity, optional
        Equivalent diameter of the annulus around the cone, d = beta * D (m).
        Data sheets usually give beta: pass ``d=beta * D``.
        Give either ``d`` or ``dc``.
    dc : float, pint.Quantity, optional
        Cone diameter at its widest section (the beta edge) (m). beta is then
        sqrt(1 - (dc / D)**2). Give either ``d`` or ``dc``.
    C : float, callable or array_like, optional
        Discharge coefficient. Options are:

        - None (default): the ISO 5167-5 value of an uncalibrated meter, 0.82;
        - a number: a calibrated discharge coefficient (e.g. the mean value
          given in the calibration certificate);
        - a callable ``C(Re)``: discharge coefficient as a function of the
          pipe Reynolds number ReD, solved by iteration;
        - a calibration table ``(Re, C)``: two sequences with the Reynolds
          numbers and the discharge coefficients measured at them. C is
          interpolated linearly in log10(Re). Outside the calibrated range C
          is held at the nearest end value and a warning is emitted, since
          ISO 5167-5 does not permit extrapolating a calibration.
    state_upstream : bool, optional
        True if ``state`` is the state at the upstream tapping. If it is the
        state downstream of the meter, use False: the upstream state is then
        taken at p + delta_p and the same temperature. The ``state`` passed in
        is not modified. Default is True.

    Attributes
    ----------
    flow_m : pint.Quantity
        Mass flow rate (kg/s).
    flow_v : pint.Quantity
        Volumetric flow rate at the upstream state (m³/s).
    state : ccp.State
        Upstream state used in the calculation.
    beta : pint.Quantity
        Diameter ratio (dimensionless).
    d, dc : pint.Quantity
        Equivalent diameter beta * D and cone diameter (m).
    C : pint.Quantity
        Discharge coefficient used (dimensionless).
    calibrated : bool
        False when the ISO 5167-5 value of an uncalibrated meter is used.
    epsilon : pint.Quantity
        Expansibility factor (dimensionless).
    reynolds : pint.Quantity
        Pipe Reynolds number, ReD = 4 qm / (pi mu D) (dimensionless).
    outside_limits : dict
        Limits that were exceeded, mapped to the warning message; empty when
        the calculation is within the limits of the standard.

    Examples
    --------
    >>> import ccp
    >>> Q_ = ccp.Q_
    >>> fluid = {"R134A": 0.018, "R1234ZE": 31.254, "N2": 67.588, "o2": 1.14}
    >>> state = ccp.State(p=Q_(10, "bar"), T=Q_(40, "degC"), fluid=fluid)
    >>> fc = ccp.FlowCone(
    ...     state, delta_p=Q_(0.1, "bar"), D=Q_(250, "mm"), dc=Q_(180, "mm")
    ... )
    >>> print(f"{fc.flow_m.to('kg/h'):.1f~P}")
    52066.7 kg/h
    >>> print(f"beta = {fc.beta.m:.4f}, ReD = {fc.reynolds.m:.3g}")
    beta = 0.6940, ReD = 4.17e+06
    """

    @check_units
    def __init__(
        self,
        state,
        delta_p,
        D,
        d=None,
        dc=None,
        C=None,
        state_upstream=True,
    ):
        if delta_p.m <= 0:
            raise ValueError(f"delta_p must be positive, got {delta_p:~P}.")

        self.D = D
        self.beta, self.d, self.dc = _cone_geometry(D, d, dc)
        self.delta_p = delta_p

        if not state_upstream:
            # keep the caller's state unchanged
            state = copy(state)
            state.update(p=state.p() + delta_p, T=state.T())
        self.state = state

        self.calibrated = C is not None
        C_of_reynolds, constant_C, calibration_range = _discharge_coefficient(C)

        # ISO 5167-5 evaluated on SI magnitudes
        D_m = D.to("m").m
        beta = self.beta.m
        dp = delta_p.to("Pa").m
        p1 = state.p().to("Pa").m
        rho = state.rho().to("kg/m**3").m
        mu = state.viscosity().to("Pa*s").m
        kappa = state.kv().to("dimensionless").m

        epsilon = 1 - (0.649 + 0.696 * beta**4) * dp / (kappa * p1)
        # flow with C = 1 and the Reynolds number per unit of mass flow
        flow_factor = (
            epsilon
            / np.sqrt(1 - beta**4)
            * (np.pi / 4)
            * (D_m * beta) ** 2
            * np.sqrt(2 * dp * rho)
        )
        reynolds_factor = 4 / (np.pi * mu * D_m)

        if C_of_reynolds is None:
            C_value = constant_C
        else:
            C_value = _solve_C(C_of_reynolds, flow_factor * reynolds_factor)

        flow_m = C_value * flow_factor
        reynolds = flow_m * reynolds_factor

        self.C = Q_(C_value, "dimensionless")
        self.epsilon = Q_(epsilon, "dimensionless")
        self.reynolds = Q_(reynolds, "dimensionless")
        self.flow_m = Q_(flow_m, "kg/s")
        self.flow_v = (self.flow_m * state.v()).to("m**3/s")

        self.outside_limits = self._check_limits(
            reynolds, (p1 - dp) / p1, calibration_range
        )
        for message in self.outside_limits.values():
            # stacklevel 3: skip this frame and the check_units wrapper
            warnings.warn(message, FlowMeterWarning, stacklevel=3)

    def _check_limits(self, reynolds, pressure_ratio, calibration_range):
        """Messages for the limits of ISO 5167-5 that are exceeded."""
        messages = {}
        uncalibrated = (
            f"the range of the uncalibrated ISO 5167-5 discharge coefficient "
            f"C = {C_ISO}; supply a calibrated C"
        )
        if not self.calibrated:
            D_min, D_max = D_LIMITS
            if not D_min <= self.D <= D_max:
                messages["D"] = (
                    f"Cone meter pipe diameter D = {self.D.to('mm'):.1f~P} is "
                    f"outside {D_min:~P} to {D_max:~P}, {uncalibrated}."
                )
            beta_min, beta_max = BETA_LIMITS
            if not beta_min <= self.beta.m <= beta_max:
                messages["beta"] = (
                    f"Cone meter beta = {self.beta.m:.4g} is outside "
                    f"{beta_min} to {beta_max}, {uncalibrated} (ISO 5167-5 "
                    f"requires meters with beta > {beta_max} to be calibrated)."
                )
            re_min, re_max = REYNOLDS_LIMITS
            if not re_min <= reynolds <= re_max:
                messages["reynolds"] = (
                    f"Cone meter Reynolds number ReD = {reynolds:.3g} is outside "
                    f"{re_min:.3g} to {re_max:.3g}, {uncalibrated}."
                )
        elif calibration_range is not None:
            re_min, re_max = calibration_range
            if not re_min <= reynolds <= re_max:
                messages["calibration"] = (
                    f"Cone meter Reynolds number ReD = {reynolds:.3g} is outside "
                    f"the calibrated range {re_min:.3g} to {re_max:.3g}; C is "
                    f"held at the nearest calibration value (ISO 5167-5 does "
                    f"not permit extrapolating a calibration)."
                )
        if pressure_ratio < PRESSURE_RATIO_MIN:
            messages["pressure_ratio"] = (
                f"Cone meter pressure ratio p2/p1 = {pressure_ratio:.4g} is "
                f"below {PRESSURE_RATIO_MIN}, the limit of the ISO 5167-5 "
                f"expansibility factor equation."
            )
        return messages


@check_units
def _cone_geometry(D, d=None, dc=None):
    """Diameter ratio, equivalent diameter and cone diameter of a cone meter.

    Raises ValueError unless exactly one of d and dc is given and it gives
    0 < beta < 1.
    """
    if (d is None) == (dc is None):
        raise ValueError(
            "Give exactly one of d (equivalent diameter, beta = d/D) and dc "
            "(cone diameter, beta = sqrt(1 - (dc/D)**2))."
        )
    if D is None or D.m <= 0:
        raise ValueError(f"D must be a positive pipe diameter, got {D}.")
    if d is not None:
        ratio = (d / D).to("dimensionless").m
        if not 0 < ratio < 1:
            raise ValueError(f"d must be between 0 and D, got d/D = {ratio:.4g}.")
        beta = ratio
        dc = D * np.sqrt(1 - beta**2)
    else:
        ratio = (dc / D).to("dimensionless").m
        if not 0 < ratio < 1:
            raise ValueError(f"dc must be between 0 and D, got dc/D = {ratio:.4g}.")
        beta = np.sqrt(1 - ratio**2)
        d = D * beta
    return Q_(beta, "dimensionless"), d.to("m"), dc.to("m")


def _discharge_coefficient(C):
    """Split the C argument into (C(Re) or None, constant C, calibrated Re range)."""
    if C is None:
        return None, C_ISO, None
    if callable(C):
        return lambda reynolds: float(C(reynolds)), None, None
    if np.ndim(C) == 0:
        return None, float(C), None
    table = np.asarray(C, dtype=float)
    if table.ndim != 2 or table.shape[0] != 2:
        raise ValueError(
            "A calibration table C must be given as (Re, C): two sequences "
            f"with the same length; got an array of shape {table.shape}."
        )
    reynolds_cal, C_cal = table[:, np.argsort(table[0])]
    if not np.all(reynolds_cal > 0):
        raise ValueError("The Reynolds numbers of the calibration table must be > 0.")
    log_reynolds_cal = np.log10(reynolds_cal)

    def C_of_reynolds(reynolds):
        return float(np.interp(np.log10(reynolds), log_reynolds_cal, C_cal))

    return C_of_reynolds, None, (reynolds_cal[0], reynolds_cal[-1])


def _solve_C(C_of_reynolds, reynolds_per_C, rtol=1e-12, maxiter=100):
    """Discharge coefficient that agrees with the Reynolds number of its flow.

    The Reynolds number is proportional to C (Re = C * reynolds_per_C), so the
    fixed point C = C(Re(C)) is iterated; it converges as long as C varies
    slowly with Re, which is the case for any calibration curve.
    """
    C = C_ISO
    for _ in range(maxiter):
        C_new = C_of_reynolds(C * reynolds_per_C)
        if abs(C_new - C) <= rtol * abs(C_new):
            return C_new
        C = C_new
    raise ValueError(
        f"The discharge coefficient C(Re) did not converge in {maxiter} "
        "iterations; check that C varies slowly with the Reynolds number."
    )
