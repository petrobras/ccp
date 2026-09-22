import warnings
from copy import copy
from functools import wraps

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import newton

import ccp.config
from ccp.config.units import Q_, check_units
from ccp.config.utilities import r_getattr
from ccp.data_io.serializers import Serializable
from ccp.roots import solve_monotone

from . import similarity
from .state import State


class PhaseWarning(UserWarning):
    """The discharge resolved with an imposed phase was not a stable state.

    Emitted when ``ccp.config.DEFAULT_PHASE`` imposed a phase on the suction
    and the discharge derived from it lies inside the phase envelope; the
    point is re-solved without imposing a phase.
    """


def _check_single_phase_suction(suc):
    """Raise ``ValueError`` when the suction lies at or inside the phase envelope.

    A state built without an imposed phase carries the vapour quality of its
    unconstrained flash (``0 <= Q <= 1`` inside the envelope on both the
    REFPROP and the HEOS backends). The discharge closures assume a
    single-phase compression, so a wet suction is reported before any solve
    instead of surfacing as a convergence failure.
    """
    if suc.phase:
        return
    try:
        quality = suc.Q()
    except ValueError:
        return
    if 0.0 <= quality <= 1.0:
        raise ValueError(
            "The suction state lies at or inside the phase envelope (vapour "
            f"quality {quality:.4g}); a compressor point needs a single-phase "
            f"suction. Suction: {suc!r}"
        )


class Point(Serializable):
    """A performance point.
    A point in the compressor map that can be defined in different ways.

    Parameters
    ----------
    speed : pint.Quantity, float
        Speed in rad/s.
    flow_v or flow_m : pint.Quantity, float
        Volumetric (m³/s) or mass (kg/s) flow.
    suc, disch : ccp.State, ccp.State
        Suction and discharge states for the point.
    suc, disch_p, eff : ccp.State, float, float
        Suction state, discharge pressure and polytropic efficiency.
    suc, head, eff : ccp.State, float, float
        Suction state, polytropic head and polytropic efficiency.
    suc, head, power : ccp.State, pint.Quantity or float, pint.Quantity or float
        Suction state, polytropic head (J/kg) and gas power (Watt).
    suc, head, power_shaft, power_losses : ccp.State, pint.Quantity or float,
        pint.Quantity or float, pint.Quantity or float
        Suction state, polytropic head (J/kg), shaft power (Watt) and power
        losses (Watt).
    suc, eff, volume_ratio : ccp.State, float, float
        Suction state, polytropic efficiency and volume ratio.
    suc, pres_ratio, disch_T : ccp.State, float, pint.Quantity or float
        Suction state, pressure ratio and discharge temperature.
    b : float, pint.Quantity
        Impeller width at the outer blade diameter (m).
    D : float, pint.Quantity
        Impeller outer diameter (m).
    power_shaft : float, pint.Quantity
        Shaft power (Watt), optional.
    power_losses : float, pint.Quantity
        Mechanical power losses (Watt), optional.
    torque : float, pint.Quantity
        Load torque (N.m), optional.
    surface_roughness : pint.Quantity, optional
        Gas passage mean surface roughness (m).
        Used in the reynolds correction calculation.
        Default value is 3.048e-6 m.
    casing_area : pint.Quantity, optional
        Compressor case area used to calculate case heat loss (m²).
    casing_temperature : pint.Quantity, optional
        Compressor case temperature used to calculate case heat loss (degK).
    ambient_temperature : pint.Quantity, optional
        Ambient temperature used to calculate case heat loss (degK).
    convection_constant : pint.Quantity, optional
        Heat transfer (convection) constant (W / m²degK).
        Default value is 13.6.
    polytropic_method : str, optional
        Polytropic method used for head and efficiency calculation.
        Options are: "mallen_saville", "sandberg_colby",
        "sandberg_colby_multistep", "schultz" and "huntington".
        The default is "sandberg_colby".
        The default value can be changed in a global level with:
        ccp.config.POLYTROPIC_METHOD = "<desired value>"
    extrapolated: bool, optional
        If true, the point is an extrapolation from other curves or its flow is
        outside surge and choke limits.
        The default is False.

    Returns
    -------
    Point : ccp.Point
        A point in the compressor map.

    Attributes
    ----------
    suc : ccp.State
        A ccp.State object.
        For more information on attributes and methods available see:
        :py:class:`ccp.State`
    disch : ccp.State
        A ccp.State object.
        For more information on attributes and methods available see:
        :py:class:`ccp.State`
    flow_v : pint.Quantity
        Volumetric flow (m³/s).
    flow_m : pint.Quantity
        Mass flow (kg/s)
    speed : pint.Quantity
        Speed (rad/s).
    head : pint.Quantity
        Polytropic head (J/kg).
    eff : pint.Quantity
        Polytropic efficiency (dimensionless).
    power : pint.Quantity
        Power (Watt).
    power_shaft : pint.Quantity
        Shaft power (Watt) which includes bearing and seal losses.
    power_losses : pint.Quantity
        Mechanical power losses (Watt) which includes bearing and seal.
    torque : pint.Quantity
        Load torque (N*m) at coupling which includes bearing and seal losses.
    phi : pint.Quantity
        Volume flow coefficient (dimensionless).
    psi : pint.Quantity
        Polytropic head coefficient (dimensionless).
    volume_ratio : pint.Quantity
        Volume ratio - suc.v() / disch.v() (dimensionless).
    b : float, pint.Quantity
        Impeller width at the outer blade diameter (m).
    D : float, pint.Quantity
        Impeller outer diameter (m).
    casing_area : pint.Quantity
        Compressor case area used to calculate case heat loss (m²).
    casing_temperature : pint.Quantity
        Compressor case temperature used to calculate case heat loss (degK).
    ambient_temperature : pint.Quantity
        Ambient temperature used to calculate case heat loss (degK).
    convection_constant : pint.Quantity
        Heat transfer (convection) constant (W / m²degK).
    reynolds : pint.Quantity
        Reynolds number (dimensionless).
    mach : pint.Quantity
        Mach number (dimensionless).
    phi_ratio : float
        Ratio between phi for this point and the original point from which it was
        converted from.
    psi_ratio : float
        Ratio between psi for this point and the original point from which it was
        converted from.
    reynolds_ratio : float
        Ratio between Reynolds for this point and the original point from which it was
        converted from.
    mach_diff : float
        Difference between Mach for this point and the original point from which it was
        converted from.
    volume_ratio_ratio : float
        Ratio between volume_ratio for this point and the original point from which it
        was converted from.
    polytropic_method : str
        Polytropic method used for head and efficiency calculation.
    extrapolated : bool
        If true, the point is an extrapolation from other curves or its flow is
        outside surge and choke limits.
        The default is False.
    """

    @check_units
    def __init__(
        self,
        suc=None,
        disch=None,
        disch_p=None,
        flow_v=None,
        flow_m=None,
        speed=None,
        head=None,
        eff=None,
        power=None,
        power_shaft=None,
        power_losses=None,
        torque=None,
        phi=None,
        psi=None,
        volume_ratio=None,
        pressure_ratio=None,
        disch_T=None,
        b=Q_(0.005, "m"),
        D=Q_(0.5, "m"),
        surface_roughness=Q_(3.175e-6, "m"),
        casing_area=None,
        casing_temperature=None,
        ambient_temperature=None,
        convection_constant=Q_(13.6, "W/(m²*degK)"),
        polytropic_method=None,
        phi_ratio=None,
        psi_ratio=None,
        reynolds_ratio=None,
        mach_diff=None,
        volume_ratio_ratio=None,
        extrapolated=False,
    ):
        if polytropic_method is None:
            self.polytropic_method = ccp.config.POLYTROPIC_METHOD
        else:
            self.polytropic_method = polytropic_method

        self.head_calc_func = globals()[f"head_pol_{self.polytropic_method}"]
        self.eff_calc_func = globals()[f"eff_pol_{self.polytropic_method}"]

        self._extrapolated = extrapolated

        self.suc = suc
        self.disch = disch
        self.disch_p = disch_p
        self.flow_v = flow_v
        self.flow_m = flow_m
        self.speed = speed
        self.head = head
        self.eff = eff
        self.power = power
        self.power_shaft = power_shaft
        self.power_losses = power_losses
        self.torque = torque

        self.phi = phi
        self.psi = psi
        self.volume_ratio = volume_ratio
        self.pressure_ratio = pressure_ratio
        self.disch_T = disch_T

        self.b = b
        self.D = D
        self.surface_roughness = surface_roughness

        self.casing_area = casing_area
        self.casing_temperature = casing_temperature
        self.ambient_temperature = ambient_temperature
        self.convection_constant = convection_constant
        self.casing_heat_loss = None

        # dummy state used to avoid copying states
        self._dummy_state = copy(self.suc)

        kwargs_dict = {}
        reasonable_ranges = {
            "eff": (0.3, 1.0),
            "head": (0, 1e15),
            "disch_p": (0, 1e15),
        }
        out_of_range_dict = {}

        for k in [
            "suc",
            "disch",
            "disch_p",
            "flow_v",
            "flow_m",
            "speed",
            "head",
            "eff",
            "power",
            "phi",
            "psi",
            "volume_ratio",
            "pressure_ratio",
            "disch_T",
            "power_losses",
            "power_shaft",
            "torque",
        ]:
            if getattr(self, k) is not None:
                kwargs_dict[k] = getattr(self, k)

        if self.suc is not None:
            _check_single_phase_suction(self.suc)

        # The point is computed by a constraint-propagation solver: given any
        # sufficient subset of the arguments above, it fills in the rest (see
        # ccp.point_solver). ``solve`` returns the required variables it could
        # not determine (empty when the point is fully defined).
        from ccp.point_solver import solve

        solver_error = None
        try:
            # the discharge closures are compressions from the suction: the
            # imposed phase may drive every flash (see State.single_phase_solver)
            with State.single_phase_solver():
                unresolved = solve(self)
        except (ValueError, RuntimeError) as exc:
            # a thermodynamic relation failed to converge, typically because an
            # argument is out of a physically reasonable range
            solver_error = exc
            unresolved = True

        if unresolved:
            kwargs_repr = (
                str(kwargs_dict)
                .replace(">", "")
                .replace("<", "")
                .replace("Quantity", "Q_")
                .replace("State", "ccp.State")
            )
            # check if some kwargs are out of reasonable range
            for k in kwargs_dict:
                if k in reasonable_ranges:
                    if (
                        not reasonable_ranges[k][0]
                        <= kwargs_dict[k].m
                        <= reasonable_ranges[k][1]
                    ):
                        # add this to the out of range dict
                        out_of_range_dict[k] = kwargs_dict[k]

            if solver_error is None:
                reason = (
                    "The provided arguments are insufficient to fully define the point."
                )
            else:
                reason = (
                    "A thermodynamic relation failed to converge: "
                    f"{type(solver_error).__name__}: {solver_error}"
                )
            message = (
                f"Could not calculate point with ccp.Point(**{kwargs_repr}).\n{reason}"
            )
            if out_of_range_dict:
                message += (
                    "\nThe following kwargs seem out of reasonable range: "
                    f"{out_of_range_dict}."
                )
            raise ValueError(message) from solver_error

        # A discharge derived under a phase imposed by ccp.config.DEFAULT_PHASE
        # is verified once against an unconstrained flash; a metastable root
        # (discharge inside the phase envelope) re-solves the point the legacy
        # way, without imposing a phase.
        if (
            "disch" not in kwargs_dict
            and ccp.config.PHASE_CHECK
            and getattr(self.suc, "_phase_auto", False)
            and not self.disch.phase_is_stable()
        ):
            self._solve_unconstrained(kwargs_dict)

        self.reynolds = reynolds(self.suc, self.speed, self.b, self.D)
        self.mach = mach(self.suc, self.speed, self.D)
        if phi_ratio is None:
            self.phi_ratio = Q_(1.0, "dimensionless")
        else:
            self.phi_ratio = phi_ratio
        if psi_ratio is None:
            self.psi_ratio = Q_(1.0, "dimensionless")
        else:
            self.psi_ratio = psi_ratio
        if reynolds_ratio is None:
            self.reynolds_ratio = Q_(1.0, "dimensionless")
        else:
            self.reynolds_ratio = reynolds_ratio
        # mach in the ptc 10 is compared with Mmt - Mmsp
        if mach_diff is None:
            self.mach_diff = Q_(0.0, "dimensionless")
        else:
            self.mach_diff = mach_diff
        # ratio between specific volume ratios in original and converted conditions
        if volume_ratio_ratio is None:
            self.volume_ratio_ratio = Q_(1.0, "dimensionless")
        else:
            self.volume_ratio_ratio = volume_ratio_ratio

        self._add_point_plot()

    def _solve_unconstrained(self, kwargs_dict):
        """Solve the point again with an unconstrained copy of the suction.

        Used when the discharge found under the phase imposed by
        ``ccp.config.DEFAULT_PHASE`` is a metastable root: every derived state
        inherits ``phase=False`` from the suction copy, so the solve follows the
        legacy (full stability analysis) path and reproduces the legacy result.
        """
        from ccp.point_solver import VAR_NAMES, solve

        warnings.warn(
            "The discharge state found with the imposed phase "
            f"'{self.suc.phase}' is not a stable state (it lies inside the phase "
            "envelope); solving the point again without imposing a phase. Set "
            "ccp.config.DEFAULT_PHASE = None to disable the phase imposition or "
            "build the suction with phase=False.",
            PhaseWarning,
            stacklevel=3,
        )
        suc = self.suc
        self.suc = State(
            p=suc.p(), T=suc.T(), fluid=suc.fluid, EOS=suc.EOS, phase=False
        )
        self._dummy_state = copy(self.suc)
        for k in VAR_NAMES:
            if k not in kwargs_dict:
                setattr(self, k, None)
        self.casing_heat_loss = None
        try:
            unresolved = solve(self)
        except RuntimeError as exc:
            raise ValueError(
                "A thermodynamic relation failed to converge while solving the "
                f"point without an imposed phase: {exc}"
            ) from exc
        if unresolved:
            raise ValueError(
                "Could not calculate the point without an imposed phase; "
                f"unresolved variables: {unresolved}."
            )

    def _add_point_plot(self):
        """Add plot to point after point is fully defined."""
        for state in ["suc", "disch"]:
            for attr in ["p", "T", "h", "s", "rho"]:
                plot = plot_func(self, ".".join([state, attr]))
                setattr(getattr(self, state), attr + "_plot", plot)
        for attr in ["head", "eff", "power", "power_shaft", "torque"]:
            plot = plot_func(self, attr)
            setattr(self, attr + "_plot", plot)

    def __str__(self):
        return (
            f"\nPoint: "
            f"\nVolume flow: {self.flow_v:.2f~P}"
            f"\nHead: {self.head:.2f~P}"
            f"\nEfficiency: {self.eff:.2f~P}"
            f"\nPower: {self.power:.2f~P}"
            f"\nShaft Power: {self.power_shaft:.2f~P}"
            f"\nTorque: {self.torque:.2f~P}"
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if (
                self.suc == other.suc
                and np.allclose(self.speed, other.speed)
                and np.allclose(self.flow_v, other.flow_v)
                and np.allclose(self.head, other.head)
                and np.allclose(self.eff, other.eff)
            ):
                return True

        return False

    def __hash__(self):
        return hash(
            (
                self.suc,
                round(self.speed.to_base_units().magnitude, 8) if self.speed else None,
                (
                    round(self.flow_v.to_base_units().magnitude, 8)
                    if self.flow_v
                    else None
                ),
                round(self.head.to_base_units().magnitude, 8) if self.head else None,
                round(self.eff.to_base_units().magnitude, 8) if self.eff else None,
            )
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(suc={self.suc},"
            f' speed=Q_("{self.speed:.0f~P}"),'
            f' flow_v=Q_("{self.flow_v:.2f~P}"),'
            f' head=Q_("{self.head:.0f~P}"),'
            f' eff=Q_("{self.eff:.3f~P}"),'
            f' power_losses=Q_("{self.power_losses:.0f~P}"))'
        )

    @classmethod
    @check_units
    def convert_from(
        cls,
        original_point,
        suc=None,
        find="speed",
        speed=None,
        reynolds_correction=False,
        **kwargs,
    ):
        """Convert point from an original point.

        The procedure to convert a point considering that the volume ratio will be
        the same, follows the following steps:
        1. Assume that eff_converted = eff_original and psi_converted = psi_original
        2. Assume that volume ratio will be the same to keep similarity
        3. Calculate discharge volume based on suction state and volume ratio
        4. Calculate discharge state using newton method to find the discharge pressure.
        Criterion for convergence is the polytropic efficiency.
        5. Calculate head based on the new discharge state
        6. Calculate speed based on head and psi

        This procedure is followed when we have find="speed".

        Parameters
        ----------
        original_point : ccp.Point
            Original point from which the desired point will be converted.
        suc : ccp.State
            New suction state.
        find : str, optional
            If the calculation will find a new speed keeping constant volume ratio,
            or a new volume ratio for the desired speed.
            Options are "speed" or "volume_ratio", default is "speed".
        speed : float, pint.Quantity, optional
            Desired speed. If find="speed", this should be None.
        reynolds_correction : bool, optional
            If reynolds correction should be applied during the conversion.
            If True the ASME PTC 10 reynolds correction is applied

        The user must provide 3 of the 4 available arguments. The argument which is
        not provided will be calculated.
        """
        if speed is None:
            speed = original_point.speed

        power_losses = (
            original_point.power_losses * (speed / original_point.speed) ** 2.5
        )

        eff_converted = original_point.eff
        psi_converted = original_point.psi
        phi_converted = original_point.phi

        if reynolds_correction == "ptc1997":
            rem_corr_eff, rem_corr_psi, rem_corr_phi = correct_reynolds_1997(
                suc,
                speed,
                original_point,
            )
            eff_converted = rem_corr_eff * original_point.eff
            psi_converted = rem_corr_psi * original_point.psi
            phi_converted = rem_corr_phi * original_point.phi
        elif reynolds_correction == "ptc2022" or reynolds_correction is True:
            rem_corr_eff, rem_corr_psi, rem_corr_phi = correct_reynolds_2022(
                suc,
                speed,
                original_point,
            )
            eff_converted = rem_corr_eff * original_point.eff
            psi_converted = rem_corr_psi * original_point.psi
            phi_converted = rem_corr_phi * original_point.phi

        convert_point_options = {
            "speed": dict(
                suc=suc,
                eff=eff_converted,
                power_losses=power_losses,
                phi=phi_converted,
                psi=psi_converted,
                volume_ratio=original_point.volume_ratio,
                b=original_point.b,
                D=original_point.D,
                **kwargs,
            ),
            "volume_ratio": dict(
                suc=suc,
                eff=eff_converted,
                power_losses=power_losses,
                phi=phi_converted,
                psi=psi_converted,
                speed=speed,
                b=original_point.b,
                D=original_point.D,
                **kwargs,
            ),
        }

        converted_point = cls(**convert_point_options[find])
        # a curve is first converted to find the new speed and then converted to
        # the mean speed. Therefore, it can be considered:
        # original point as the base point (reference for the conversion)
        # original point as the test point for Performance Test app conversion
        converted_point.phi_ratio = (
            converted_point.phi / original_point.phi
        ) * original_point.phi_ratio
        converted_point.psi_ratio = (
            converted_point.psi / original_point.psi
        ) * original_point.psi_ratio
        converted_point.volume_ratio_ratio = (
            converted_point.volume_ratio / original_point.volume_ratio
        ) * original_point.volume_ratio_ratio
        converted_point.reynolds_ratio = (
            converted_point.reynolds / original_point.reynolds
        ) * original_point.reynolds_ratio
        converted_point.mach_diff = (
            converted_point.mach - original_point.mach
        ) + original_point.mach_diff

        return converted_point

    def __getstate__(self):
        # plot closures are rebuilt on load; the dummy state is a scratch copy
        # of the suction (one state less to re-flash per pickled point)
        attributes = self.__dict__.copy()
        final_attributes = {
            k: v
            for k, v in attributes.items()
            if "plot" not in k and k != "_dummy_state"
        }

        return final_attributes

    def __setstate__(self, state):
        self.__dict__ = state
        if "_dummy_state" not in state:
            self._dummy_state = copy(self.suc)
        self._add_point_plot()

    def to_dict(self):
        """Return a dict representation of the point.

        Quantities are converted to strings (e.g. "100000.0 pascal") so that
        the dict can be serialized to formats such as toml or json.

        Returns
        -------
        dict
            Dict with the parameters that define the point.
        """
        # a phase imposed by ccp.config.DEFAULT_PHASE is a runtime policy, not
        # part of the point's definition: store the user's intent instead
        if getattr(self.suc, "_phase_auto", False):
            phase = None
        else:
            phase = self.suc.phase
        return dict(
            p=str(self.suc.p()),
            T=str(self.suc.T()),
            fluid=self.suc.fluid,
            phase=str(phase),
            speed=str(self.speed),
            flow_v=str(self.flow_v),
            head=str(self.head),
            eff=str(self.eff),
            power_losses=str(self.power_losses),
            b=str(self.b),
            D=str(self.D),
            polytropic_method=str(self.polytropic_method),
            phi_ratio=str(self.phi_ratio),
            psi_ratio=str(self.psi_ratio),
            reynolds_ratio=str(self.reynolds_ratio),
            mach_diff=str(self.mach_diff),
            volume_ratio_ratio=str(self.volume_ratio_ratio),
            extrapolated=str(self._extrapolated),
        )

    @classmethod
    def from_dict(cls, dict_parameters):
        """Create a point from a dict created with :meth:`to_dict`.

        Parameters
        ----------
        dict_parameters : dict
            Dict as generated by :meth:`to_dict`.

        Returns
        -------
        point : ccp.Point
            Point object.
        """
        dict_parameters = dict(dict_parameters)
        dict_parameters.pop("ccp_version", None)
        phase = dict_parameters.pop("phase", None)
        # backwards compatibility: older files store no phase, newer ones may
        # store the string "None" when no phase was forced.
        if phase in (None, "None", ""):
            phase = None
        elif phase in (False, "False"):
            # the suction opted out of ccp.config.DEFAULT_PHASE
            phase = False
        suc = State(
            p=Q_(dict_parameters.pop("p")),
            T=Q_(dict_parameters.pop("T")),
            fluid=dict_parameters.pop("fluid"),
            phase=phase,
        )
        extrapolated = dict_parameters.pop("extrapolated", False)
        # Convert string to boolean if needed (for backwards compatibility)
        if isinstance(extrapolated, str):
            extrapolated = extrapolated.lower() == "true"
        polytropic_method = dict_parameters.pop("polytropic_method", None)

        return cls(
            suc=suc,
            extrapolated=extrapolated,
            polytropic_method=polytropic_method,
            **{k: Q_(v) for k, v in dict_parameters.items()},
        )

    def mach_limits(self, mmsp=None):
        """Calculate Mach lower and upper limits.

        Parameters
        ----------
        mmsp : float, optional
            Mach number specified. Default value is the point Mach number.

        Returns
        -------
        limits : dict
            Dict with keys: 'lower', 'upper' and 'within_limits'.
        """
        if mmsp is None:
            mmsp = self.mach.m - self.mach_diff.m
        if 0 <= mmsp < 0.215:
            lower_limit = 0
            upper_limit = 0.286 + 0.75 * mmsp
        elif 0.215 <= mmsp <= 0.86:
            lower_limit = 1.266 * mmsp - 0.271
            upper_limit = 0.286 + 0.75 * mmsp
        elif mmsp > 0.86:
            lower_limit = mmsp - 0.042
            upper_limit = mmsp + 0.07
        else:
            raise ValueError("Mach number out of specified range.")

        if lower_limit <= self.mach_diff + mmsp <= upper_limit:
            within_limits = True
        else:
            within_limits = False

        return {
            "lower": lower_limit,
            "upper": upper_limit,
            "within_limits": within_limits,
        }

    def plot_mach(self, fig=None, **kwargs):
        """Plot allowable Mach range and point.

        This will plot the allowable Mach range and the point according to the
        PTC criteria.

        The x-axis represents the Specified Machine Mach Number for the point.
        The y-axis represents the Test Machine Mach Number from the original point.

        Parameters
        ----------
        fig : plotly.Figure
            Plotly figure.

        Returns
        -------
        fig : plotly.Figure
            Plotly figure.
        """
        if fig is None:
            fig = go.Figure()

        # build acceptable region
        upper_limit = []
        lower_limit = []
        mmsp_range = np.linspace(0, 1.2, 300)
        for mmsp in mmsp_range:
            mach_limits = self.mach_limits(mmsp)
            lower_limit.append(mach_limits["lower"])
            upper_limit.append(mach_limits["upper"])

        fig.add_trace(
            go.Scatter(
                x=mmsp_range, y=lower_limit, line=dict(color="blue", dash="dash")
            )
        )
        fig.add_trace(
            go.Scatter(x=mmsp_range, y=upper_limit, line=dict(color="red", dash="dash"))
        )

        # add point
        fig.add_trace(
            go.Scatter(
                x=[self.mach],
                y=[self.mach_diff + self.mach],
                marker=dict(color="black"),
                mode="markers",
                hovertemplate=(
                    "Specified Mach (Mm<sub>sp</sub>): %{x:.3f}<br>"
                    "Test Mach (Mm<sub>t</sub>): %{y:.3f}<extra></extra>"
                ),
            )
        )
        # subscripts for t and sp
        _t = "\u209c"
        _sp = "\u209b\u209a"
        space_str = "&nbsp;"
        fig.update_xaxes(
            title=f"Specified Machine Mach Number - Mm{_sp}",
        )
        fig.update_yaxes(
            title=f"Test Machine Mach Number - Mm{_t}",
        )
        fig.update_xaxes(
            range=[0, 1.2],
            tickformat=".1f",
            dtick=0.1,
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
        )
        fig.update_yaxes(
            range=[0, 1.2],
            tickformat=".1f",
            dtick=0.1,
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
        )
        # Upper Limit text
        upper_text = (
            "<b>Upper Limit</b><br>"
            f"Mm{_t} = (0.286 + 0.75·Mm{_sp}) {2 * space_str}for Mm{_sp} ≤ 0.86<br>"
            f"Mm{_t} = (Mm{_sp} + 0.07) {8 * space_str}for Mm{_sp} > 0.86"
        )

        # Lower Limit text
        lower_text = (
            "<b>Lower Limit</b><br>"
            f"Mm{_t} = 0 {20 * space_str}for Mm{_sp} < 0.215<br>"
            f"Mm{_t} = (1.266·Mm{_sp} - 0.271) {space_str}"
            f"for 0.215 ≤ Mm{_sp} ≤ 0.86<br>"
            f"Mm{_t} = (Mm{_sp} - 0.042) {7 * space_str}for Mm{_sp} > 0.86"
        )

        # Annotation: Upper Limit (top-left corner)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.96,
            xanchor="left",
            yanchor="top",
            align="left",
            showarrow=False,
            text=upper_text,
            font=dict(size=10, family="monospace"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(0,0,0,0.45)",
            borderwidth=1,
            borderpad=6,
        )

        # Annotation: Lower Limit (bottom-right corner)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.98,
            y=0.08,
            xanchor="right",
            yanchor="bottom",
            align="left",
            showarrow=False,
            text=lower_text,
            font=dict(size=10, family="monospace"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(0,0,0,0.45)",
            borderwidth=1,
            borderpad=6,
        )
        fig.update_layout(showlegend=False)

        return fig

    def reynolds_limits(self, remsp=None):
        """Calculate Reynolds lower and upper limits.

        Parameters
        ----------
        remsp : float, optional
            Reynolds number specified. Default value is the point reynolds number.

        Returns
        -------
        limits : dict
            Dict with keys: 'lower', 'upper' and 'within_range'.
        """
        if remsp is None:
            remsp = self.reynolds / self.reynolds_ratio.m

        lower_limit, upper_limit = similarity.reynolds_limits(
            _magnitude(remsp, "dimensionless")
        )

        if lower_limit <= self.reynolds_ratio * remsp <= upper_limit:
            within_limits = True
        else:
            within_limits = False

        return {
            "lower": lower_limit,
            "upper": upper_limit,
            "within_limits": within_limits,
        }

    def plot_reynolds(self, fig=None, **kwargs):
        """Plot allowable Reynolds range and point.

        This will plot the allowable Mach range and the point according to the
        PTC criteria.

        The x-axis represents the Specified Machine Reynolds Number for the point.
        The y-axis represents the Test Machine Reynolds Number from the original point.

        Parameters
        ----------
        fig : plotly.Figure
            Plotly figure.

        Returns
        -------
        fig : plotly.Figure
            Plotly figure.
        """
        # build acceptable region
        upper_limit = []
        lower_limit = []
        remsp_range = np.geomspace(9e4, 1e10, 300)
        for remsp in remsp_range:
            reynolds_limits = self.reynolds_limits(remsp)
            lower_limit.append(reynolds_limits["lower"])
            upper_limit.append(reynolds_limits["upper"])

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=remsp_range, y=lower_limit, line=dict(color="blue", dash="dash")
            )
        )
        fig.add_trace(
            go.Scatter(
                x=remsp_range, y=upper_limit, line=dict(color="red", dash="dash")
            )
        )

        # add point
        fig.add_trace(
            go.Scatter(
                x=[self.reynolds.m],
                y=[self.reynolds_ratio * self.reynolds.m],
                marker=dict(color="black"),
                mode="markers",
                hovertemplate=(
                    "Specified Reynolds (Rem<sub>sp</sub>): %{x:.3e}<br>"
                    "Test Reynolds (Rem<sub>t</sub>): %{y:.3e}<extra></extra>"
                ),
            )
        )

        # subscripts for t and sp
        _t = "\u209c"
        _sp = "\u209b\u209a"
        space_str = "&nbsp;"
        fig.update_xaxes(
            type="log",
            tickformat=".1e",
            tickmode="array",
            tickvals=[10**i for i in range(4, 11)],  # Show tick labels only at 1eX
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
            minor=dict(
                tickvals=[j * 10**i for i in range(4, 11) for j in range(2, 10)],
                showgrid=True,
                gridcolor="rgba(200,200,200,0.4)",
                gridwidth=0.5,
            ),
            title=f"Specified Machine Reynolds Number- Rem{_sp}",
            range=[4, 10],
        )
        fig.update_yaxes(
            type="log",
            tickformat=".1e",
            tickmode="array",
            tickvals=[10**i for i in range(4, 13)],
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
            minor=dict(
                tickvals=[j * 10**i for i in range(4, 12) for j in range(2, 10)],
                showgrid=True,
                gridcolor="rgba(200,200,200,0.4)",
                gridwidth=0.5,
            ),
            title=f"Test Machine Reynolds Number - Rem{_t}",
            range=[4, 12],
        )

        # upper limit text
        upper_text = (
            "<b>Upper Limit</b><br>"
            f"Rem{_t} = 10<sup>ul</sup> {9 * space_str} for 9e4 ≤ Rem{_sp} < 8e5<br>"
            f"Rem{_t} = Rem{_sp} * 100 {space_str} for Rem{_sp} ≥ 8e5<br>"
            "where<br>"
            f"ul = 68.205 + 16.13 * log10(Rem{_sp})<br>"
            f"- 64.008 * \u221alog10(Rem{_sp})"
        )

        # lower limit text
        lower_text = (
            "<b>Lower Limit</b><br>"
            f"Rem{_t} = 10<sup>ll</sup> {10 * space_str}for 9e4 ≤ Rem{_sp} < 5e5<br>"
            f"Rem{_t} = Rem{_sp} * 0.1 {2 * space_str}for Rem{_sp} ≥ 5e5<br>"
            "where<br>"
            f"ll = -22.733 - 4.247 * log10(Rem{_sp})<br>"
            f"+ 21.63 * \u221alog10(Rem{_sp})"
        )

        # Annotation: Upper Limit (top-left corner)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.96,
            xanchor="left",
            yanchor="top",
            align="left",
            showarrow=False,
            text=upper_text,
            font=dict(size=10, family="monospace"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(0,0,0,0.45)",
            borderwidth=1,
            borderpad=6,
        )

        # Annotation: Lower Limit (bottom-right corner)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.99,
            y=0.02,
            xanchor="right",
            yanchor="bottom",
            align="left",
            showarrow=False,
            text=lower_text,
            font=dict(size=10, family="monospace"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(0,0,0,0.45)",
            borderwidth=1,
            borderpad=6,
        )

        fig.update_layout(showlegend=False)

        return fig

    def similarity_table(self, fig=None, **kwargs):
        """Plot similarity table.

        This table show the values for the non dimensional numbers (Mach, Reynolds
        and Volume ratio) and their calculated relations with respect to the
        original points used in the conversion (in the formulas, 'c' means converted
        points and 'o' means original point).

        If values are within limits, relation cells are colored in green, otherwise
        they are colored in red.

        """
        if fig is None:
            fig = go.Figure()

        quantity = [
            "Ratio of Specific Volume",
            "Flow Coefficient",
            "Mach Number",
            "Reynolds Number",
        ]
        abbrev = ["v<sub>i</sub> / v<sub>d</sub>", "φ", "Mm", "Rem"]
        original_point_value = [
            f"{self.volume_ratio.m / self.volume_ratio_ratio.m:.3f}",
            f"{self.phi.m / self.phi_ratio.m:.3f}",
            f"{self.mach.m - self.mach_diff.m:.3f}",
            f"{self.reynolds.m / self.reynolds_ratio.m:.3e}",
        ]
        formula = [
            "(v<sub>i</sub> / v<sub>d</sub>)<sub>c</sub> / "
            "(v<sub>i</sub> / v<sub>d</sub>)<sub>o</sub>",
            "φ<sub>c</sub> / φ<sub>o</sub>",
            "Mm<sub>c</sub>",
            "Rem<sub>c</sub>",
        ]
        relation = [
            f"{self.volume_ratio_ratio.m:.3f}",
            f"{self.phi_ratio.m:.3f}",
            f"{self.mach.m:.3f}",
            f"{self.reynolds.m:.3e}",
        ]
        mmsp = self.mach - self.mach_diff
        remsp = self.reynolds / self.reynolds_ratio
        mach_limits = self.mach_limits(mmsp=mmsp)
        reynolds_limits = self.reynolds_limits(remsp=remsp)
        lower_limit = [
            0.95,
            0.96,
            f"{mach_limits['lower']:.3f}",
            f"{reynolds_limits['lower']:.3e}",
        ]
        upper_limit = [
            1.05,
            1.04,
            f"{mach_limits['upper']:.3f}",
            f"{reynolds_limits['upper']:.3e}",
        ]

        if 0.95 < self.volume_ratio_ratio < 1.05:
            volume_ratio_within_limits = True
        else:
            volume_ratio_within_limits = False

        if 0.96 < self.volume_ratio_ratio < 1.04:
            phi_within_limits = True
        else:
            phi_within_limits = False

        light_green = "#D8F3DC"
        dark_green = "#2D6A4F"
        light_red = "#FFB3C1"
        dark_red = "#A4133C"

        rel_fill_color = []
        rel_font_color = []
        for status in [
            volume_ratio_within_limits,
            phi_within_limits,
            mach_limits["within_limits"],
            reynolds_limits["within_limits"],
        ]:
            if status is True:
                rel_fill_color.append(light_green)
                rel_font_color.append(dark_green)
            else:
                rel_fill_color.append(light_red)
                rel_font_color.append(dark_red)

        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=[
                            "<b>Quantity</b>",
                            "<b></b>",
                            "<b>Original Point Value</b>",
                            "<b></b>",
                            "<b>Converted Point Value</b>",
                            "<b>Lower Limit</b>",
                            "<b>Upper Limit</b>",
                        ],
                        line_color="white",
                        fill_color="white",
                        align="center",
                        font=dict(color="black", size=12),
                    ),
                    cells=dict(
                        values=[
                            quantity,
                            abbrev,
                            original_point_value,
                            formula,
                            relation,
                            lower_limit,
                            upper_limit,
                        ],
                        line_color=[
                            "white",
                            "white",
                            "white",
                            "white",
                            "white",
                            "white",
                            "white",
                        ],
                        fill_color=[
                            "white",
                            "white",
                            "white",
                            "white",
                            rel_fill_color,
                            "white",
                            "white",
                        ],
                        align="center",
                        font=dict(
                            color=[
                                "black",
                                "black",
                                "black",
                                "black",
                                rel_font_color,
                                "black",
                                "black",
                            ],
                            size=[12],
                        ),
                    ),
                )
            ]
        )

        return fig

    def plot_similarity(self, fig=None, **kwargs):
        """Plot similarity results.

        Plots the similarity results showing the Mach and Reynolds plots with
        their respective limits and also a table summarizing the results comparing
        the current (converted) point to the original point.

        Parameters
        ----------
        fig : plotly.Figure
            Plotly figure.

        Returns
        -------
        fig : plotly.Figure
            Plotly figure.
        """
        if fig is None:
            fig = make_subplots(
                rows=2,
                cols=2,
                specs=[
                    [{"type": "xy"}, {"type": "xy"}],
                    [{"type": "table", "colspan": 2}, None],
                ],
            )

        stable = self.similarity_table()
        mach = self.plot_mach()
        reynolds = self.plot_reynolds()

        for data in mach.data:
            data.showlegend = False
            fig.append_trace(data, row=1, col=1)

        for data in reynolds.data:
            data.showlegend = False
            fig.append_trace(data, row=1, col=2)

        for data in stable.data:
            fig.append_trace(data, row=2, col=1)

        fig.update_xaxes(mach.layout.xaxis, row=1, col=1)
        fig.update_xaxes(reynolds.layout.xaxis, row=1, col=2)
        fig.update_yaxes(mach.layout.yaxis, row=1, col=1)
        fig.update_yaxes(reynolds.layout.yaxis, row=1, col=2)

        return fig


def plot_func(self, attr):
    def inner(*args, plot_kws=None, similarity=None, **kwargs):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments flow_v_units='...' and
        attr_units='...'.
        """
        fig = kwargs.pop("fig", None)
        color = kwargs.pop("color", None)
        symbol = "circle"
        size = 6
        line = None
        customdata = None
        hovertemplate = None
        hoverlabel = None
        color_marker = color

        if similarity:
            line = dict(color="black", width=1)
            data_similarity = {
                "volume_ratio_ratio": [self.volume_ratio_ratio.m],
                "phi_ratio": [self.phi_ratio.m],
                "mach": [self.mach.m],
                "reynolds": [self.reynolds.m],
                "volume_ratio_limits": [
                    [
                        0.95,
                        1.05,
                        (
                            True
                            if self.volume_ratio_ratio > 0.95
                            and self.volume_ratio_ratio < 1.05
                            else False
                        ),
                    ]
                ],
                "phi_ratio_limits": [
                    [
                        0.96,
                        1.04,
                        (
                            True
                            if self.phi_ratio > 0.96 and self.phi_ratio < 1.04
                            else False
                        ),
                    ]
                ],
                "mach_limits": [
                    [
                        v.m if i != 2 else v
                        for i, v in enumerate(
                            self.mach_limits(mmsp=self.mach - self.mach_diff).values()
                        )
                    ]
                ],
                "reynolds_limits": [
                    [
                        v.m if i != 2 else v
                        for i, v in enumerate(
                            self.reynolds_limits(
                                remsp=self.reynolds / self.reynolds_ratio
                            ).values()
                        )
                    ]
                ],
            }
            df_similarity = pd.DataFrame(data_similarity)
            customdata = (
                df_similarity[
                    [
                        "volume_ratio_ratio",
                        "phi_ratio",
                        "mach",
                        "reynolds",
                        "volume_ratio_limits",
                        "phi_ratio_limits",
                        "mach_limits",
                        "reynolds_limits",
                    ]
                ]
                .iloc[0]
                .values.tolist()
            )
            color_marker = [
                (
                    "#7EE38D"
                    if np.all([customdata[i][2] for i in range(4, 8)])
                    else "#FC9FB0"
                )
            ]
            size = 6
            hoverlabel = dict(namelength=-1, font=dict(family="monospace"))
            # Using non-breaking spaces for alignment, same as plot_mach
            space_str = "&nbsp;"
            # Validation icons: green check or red X
            volume_icon = "✓" if customdata[4][2] else "✗"
            phi_icon = "✓" if customdata[5][2] else "✗"
            mach_icon = "✓" if customdata[6][2] else "✗"
            reynolds_icon = "✓" if customdata[7][2] else "✗"
            hovertemplate = (
                f"<span style='color: {'green' if customdata[4][2] else 'red'}'>"
                f"{volume_icon}</span>"
                "<b>(v<sub>i</sub>/v<sub>d</sub>)<sub>c</sub>/(v<sub>i</sub>/v<sub>d</sub>)"
                "<sub>o</sub>:</b> "
                f"%{{customdata[0]:.3f}}{4 * space_str}<b>limits:</b> "
                f"%{{customdata[4][0]:.3f}} - %{{customdata[4][1]:.3f}}<br>"
                f"<span style='color: {'green' if customdata[5][2] else 'red'}'>"
                f"{phi_icon}</span> {10 * space_str}"
                "<b>φ<sub>c</sub>/φ<sub>o</sub>:</b> "
                f"%{{customdata[1]:.3f}}{4 * space_str}<b>limits:</b> "
                f"%{{customdata[5][0]:.3f}} - %{{customdata[5][1]:.3f}}<br>"
                f"<span style='color: {'green' if customdata[6][2] else 'red'}'>"
                f"{mach_icon}</span> {12 * space_str}<b>Mm<sub>c</sub>:</b> "
                f"%{{customdata[2]:.4f}}{3 * space_str}<b>limits:</b> "
                f"%{{customdata[6][0]:.4f}} - %{{customdata[6][1]:.4f}}<br>"
                f"<span style='color: {'green' if customdata[7][2] else 'red'}'>"
                f"{reynolds_icon}</span> {11 * space_str}<b>Rem<sub>c</sub>:</b> "
                f"%{{customdata[3]:.3e}}{space_str}<b>limits:</b> "
                f"%{{customdata[7][0]:.3e}} - %{{customdata[7][1]:.3e}}"
                "<extra></extra>"
            )

        marker = dict(color=color_marker, symbol=symbol, size=size, line=line)

        if fig is None:
            fig = go.Figure()

        if plot_kws is None:
            plot_kws = {}

        point_attr = r_getattr(self, attr)
        if callable(point_attr):
            point_attr = point_attr()

        flow_v_units = kwargs.get("flow_v_units", self.flow_v.units)
        # Split in '.' for cases such as disch.rho.
        # In this case the user gives rho_units instead of disch.rho_units
        attr_units = kwargs.get(f"{attr.split('.')[-1]}_units", point_attr.units)

        if attr_units is not None:
            point_attr = point_attr.to(attr_units)

        value = getattr(point_attr, "magnitude")

        flow_v = self.flow_v
        name = kwargs.get(
            "name", f"Flow: {flow_v.to(flow_v_units).m:.2f}, {attr}: {value:.2f}"
        )

        if self._extrapolated:
            name = name + "<br>(extrapolated)"

        if flow_v_units is not None:
            flow_v = flow_v.to(flow_v_units)

        fig.add_trace(
            go.Scatter(
                x=[flow_v],
                y=[value],
                name=name,
                marker=marker,
                customdata=[customdata],
                hovertemplate=hovertemplate,
                hoverlabel=hoverlabel,
                **plot_kws,
            )
        )

        return fig

    return inner


def n_exp(suc, disch):
    r"""Polytropic exponent.

    The polytropic exponent :math:`n` is calculated as per :cite:`schultz1962` eq. 27:

    .. math::

        \begin{equation}
            n = \frac{\log{\frac{p_d}{p_s}}}{\log{\frac{v_s}{v_d}}}
        \end{equation}

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    n_exp : float
        Polytropic exponent.
    """
    ps = suc.p()
    vs = 1 / suc.rho()
    pd = disch.p()
    vd = 1 / disch.rho()

    return np.log(pd / ps) / np.log(vs / vd)


def head_pol(suc, disch):
    r"""Polytropic head.

    The polytropic head is calculated as per :cite:`schultz1962` eq. 27:

    .. math::

       \begin{equation}
          H_p = (\frac{n}{n - 1}) (p_d v_d - p_s v_s)
       \end{equation}

    And :math:`n` is calculated by :py:func:`n_exp`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol : pint.Quantity
        Polytropic head (J/kg).
    """

    n = n_exp(suc, disch)

    p2 = disch.p()
    v2 = 1 / disch.rho()
    p1 = suc.p()
    v1 = 1 / suc.rho()

    return (n / (n - 1)) * (p2 * v2 - p1 * v1).to("joule/kilogram")


def eff_pol(suc, disch):
    """Polytropic efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol : pint.Quantity
        Polytropic efficiency (dimensionless).

    """
    wp = head_pol(suc, disch)

    dh = disch.h() - suc.h()

    return wp / dh


def head_isentropic(suc, disch, disch_s=None):
    """Isentropic head.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.
    disch_s : ccp.State, optional
        Reusable state object to avoid copying. If provided, this state
        will be updated and used for calculations. If None, a copy of
        disch will be created.

    Returns
    -------
    head_isentropic : pint.Quantity
        Isentropic head.
    """
    # define state to isentropic discharge using dummy state
    if disch_s is None:
        disch_s = copy(disch)

    disch_s.update(p=disch.p(), s=suc.s())

    return head_pol(suc, disch_s).to("joule/kilogram")


def eff_isentropic(suc, disch):
    """Isentropic efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_isentropic : pint.Quantity
        Isentropic efficiency.
    """
    ws = head_isentropic(suc, disch)
    dh = disch.h() - suc.h()

    return ws / dh


def f_schultz(suc, disch, disch_s=None):
    r"""Correction factor as per :cite:`schultz1962` eq 32:

    .. math::

       \begin{equation}
          f = \frac{H_{ds} - H_s}{(\frac{n_s}{n_s - 1})(p_d v_{ds} - p_s v_s)}
       \end{equation}


    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.
    disch_s : ccp.State, optional
        Reusable state object to avoid copying. If provided, this state
        will be updated and used for calculations. If None, a copy of
        disch will be created.

    Returns
    -------
    f_schultz : float
        Schultz polytropic factor.
    """

    # define state to isentropic discharge using dummy state
    if disch_s is None:
        disch_s = copy(disch)

    disch_s.update(p=disch.p(), s=suc.s())

    h2s_h1 = disch_s.h() - suc.h()
    h_isen = head_isentropic(suc, disch, disch_s)

    return h2s_h1 / h_isen


def head_pol_schultz(suc, disch, disch_s=None):
    r"""Polytropic head corrected by the :cite:`schultz1962` factor.

    .. math::

       \begin{equation}
          H_{p_{schultz}} = f_{schultz} H_p
       \end{equation}

    Where :math:`f_{schultz}` is calculated by :py:func:`f_schultz` and
    :math:`H_p` is calculated by :py:func:`head_pol`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.
    disch_s : ccp.State, optional
        Reusable state object to avoid copying. If provided, this state
        will be passed to f_schultz for reuse.

    Returns
    -------
    head_pol_schultz : pint.Quantity
        Schultz polytropic head (J/kg).
    """
    f = f_schultz(suc, disch, disch_s)
    head = head_pol(suc, disch)

    return f * head


def eff_pol_schultz(suc, disch, disch_s=None):
    """Polytropic efficiency as per :cite:`schultz1962`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.
    disch_s : ccp.State, optional
        Reusable state object to avoid copying. If provided, this state
        will be passed to head_pol_schultz for reuse.

    Returns
    -------
    eff_pol_schultz : pint.Quantity
        Schultz polytropic efficiency (dimensionless).
    """
    wp = head_pol_schultz(suc, disch, disch_s)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


def head_pol_mallen_saville(suc, disch, disch_s=None):
    r"""Polytropic head as per :cite:`mallen1977polytropic` calculated with:

    .. math::

       \begin{equation}
          H_p = (h_d - h_s) - (s_d - s_s) \frac{T_d - Ts}{\ln{(\frac{T_d}{T_s})}}
       \end{equation}

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol_mallen_saville : pint.Quantity
        Mallen-Saville polytropic polytropic head (J/kg).
    """

    head = (disch.h() - suc.h()) - (disch.s() - suc.s()) * (
        disch.T() - suc.T()
    ) / np.log(disch.T() / suc.T())

    return head


def eff_pol_mallen_saville(suc, disch, disch_s=None):
    """Polytropic efficiency as per :cite:`mallen1977polytropic`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol_mallen_saville : pint.Quantity
        Mallen-Saville polytropic efficiency (dimensionless).
    """
    wp = head_pol_mallen_saville(suc, disch)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


_ref_H = 0


def head_reference(suc, disch, num_steps=100):
    r"""Reference head.

    The reference head consists of the integration of :math:`v dp` along the
    polytropic path as described by :cite:`huntington1985` and
    :cite:`sandberg2013limitations`.
    To achieve this we break the polytropic path into a series of subpaths.
    The compression ratio :math:`R_{c_i}` for each segment, as described by
    :cite:`sandberg2013limitations` is calculated with:

    .. math::

       \begin{equation}
          R_{c_i} = \sqrt[n_{steps}]{\frac{p_d}{p_s}}
       \end{equation}


    The calculation consists of two loops.
    One converges the :math:`T_1` temperature at each step by evaluating the
    difference between :math:`H = v_{avg} \Delta_p` and :math:`H = e \Delta_h`.
    The other evaluates the efficiency by checking the difference between
    the last :math:`T_1` to the discharge temperature :math:`T_d`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_reference : pint.Quantity
       Reference head as described by :cite:`huntington1985`. (J/kg).
    eff_reference : float
        Reference efficiency as described by :cite:`huntington1985` (dimensionless).
    """

    def calc_step_discharge_temp(T1, p1, p0, h0, v0, e):
        s1 = State(p=p1, T=T1, fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
        h1 = s1.h()

        vm = (v0 + s1.v()) / 2
        delta_p = Q_(p1 - p0, "Pa")
        H0 = vm * delta_p
        H1 = e * (h1 - h0)

        return (H1 - H0).magnitude

    def calc_eff(e, suc, disch):
        rc = (disch.p().m / suc.p().m) ** (1 / num_steps)
        p_intervals = [suc.p().m]
        p = suc.p().m
        for i in range(num_steps):
            next_p = p * rc
            p = next_p
            p_intervals.append(p)

        T0 = suc.T().magnitude

        global _ref_H

        _ref_H = 0

        # TODO implement p_intervals considering pressure ratio
        for p0, p1 in zip(p_intervals[:-1], p_intervals[1:]):
            s0 = State(p=p0, T=T0, fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
            T1 = newton(
                calc_step_discharge_temp, (T0 + 1e-3), args=(p1, p0, s0.h(), s0.v(), e)
            )
            s1 = State(p=p1, T=T1, fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
            _ref_H += head_pol(s0, s1)

            T0 = T1

        return disch.T().magnitude - T1

    _ref_eff = newton(calc_eff, 0.8, args=(suc, disch))

    return _ref_H, _ref_eff


_ref_H_2017 = 0


def head_reference_2017(suc, disch, num_steps=100):
    r"""Reference head.

    The reference head consists of the integration along the
    polytropic path as described by :cite:`huntington2017`.
    Contrary to the method presented by :cite:`huntington1985`, this method does
    not use a specific volume linearized over each step of the integration, instead,
    it is based on the assumption that the compressibility factor varies linearly
    with the pressure within each step.

    In this case the inner loop of the method is calculated by:

    .. math::

       \begin{equation}
          a = \frac{z_i (\frac{p_{i+1}}{p_i}) - z_{i+1}}
          {(\frac{p_{i+1}}{p_i} - 1)} \\
          b = \frac{z_{i+1} - z_i}
          {(\frac{p_{i+1}}{p_i} - 1)} \\
          (s_{i+1} - s_i) = R \frac{(1-e)}{e}(
          a \ln{(\frac{p_{i+1}}{p_i})} + b(\frac{p_{i+1}}{p_i} - 1))
      \end{equation}


    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_reference : pint.Quantity
       Reference head as described by :cite:`huntington2017`. (J/kg).
    eff_reference : float
        Reference efficiency as described by :cite:`huntington2017` (dimensionless).
    """
    R = suc.gas_constant() / suc.molar_mass()
    rc = (disch.p().m / suc.p().m) ** (1 / num_steps)
    p_intervals = [suc.p().m]
    p = suc.p().m
    for i in range(num_steps):
        next_p = p * rc
        p = next_p
        p_intervals.append(p)

    state1 = ccp.State(
        p=suc.p(), s=suc.s(), fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase
    )

    def calc_step_discharge_z(s1, s0, p1, p0, z0, R, e):
        state1.update(p=p1, s=s1)
        z1 = state1.z()
        a = (z0 * (p1 / p0) - z1) / ((p1 / p0) - 1)
        b = (z1 - z0) / ((p1 / p0) - 1)

        return (
            (R * ((1 - e) / e)) * (a * np.log(p1 / p0) + b * ((p1 / p0) - 1))
            - (state1.s() - Q_(s0, state1.s().units))
        ).magnitude

    def calc_eff(e, suc, disch, p_intervals):
        global _ref_H_2017
        _ref_H_2017 = 0
        s0 = suc.s().magnitude

        for p0, p1 in zip(p_intervals[:-1], p_intervals[1:]):
            state0 = ccp.State(
                p=p0, s=s0, fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase
            )
            z0 = state0.z()

            s1 = newton(calc_step_discharge_z, (s0 + 1e-8), args=(s0, p1, p0, z0, R, e))
            state1 = ccp.State(
                p=p1, s=s1, fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase
            )
            _ref_H_2017 += ccp.point.head_pol(state0, state1)

            s0 = s1
            T1 = state1.T().magnitude

        return disch.T().magnitude - T1

    eff0 = ccp.point.eff_pol_huntington(suc, disch)
    _ref_eff = newton(calc_eff, eff0, args=(suc, disch, p_intervals))

    return _ref_H_2017, _ref_eff


def f_sandberg_colby(suc, disch):
    r"""Correction factor as proposed by :cite:`sandberg2013limitations`.

    .. math::

       \begin{equation}
          f_p =
           \frac{(h_d - h_s) - T_{avg} (s_d - s_s)}
          {(\frac{n}{n-1})(p_d v_d - p_s v_s)}
       \end{equation}

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
     f_sandberg_colby : pint.Quantity
         Polytropic head correction factor as described by
         :cite:`sandberg2013limitations` (dimensionless).
    """
    Tm = (suc.T() + disch.T()) / 2
    hd = disch.h()
    hs = suc.h()
    sd = disch.s()
    ss = suc.s()
    n = n_exp(suc, disch)
    pd = disch.p()
    ps = suc.p()
    vd = disch.v()
    vs = suc.v()

    f_sandberg_colby = ((hd - hs) - Tm * (sd - ss)) / (
        (n / (n - 1)) * (pd * vd - ps * vs)
    )

    return f_sandberg_colby.to("dimensionless")


def head_pol_sandberg_colby(suc, disch, disch_s=None):
    r"""Polytropic head method as described in section 5-2.2 of :cite:`asmePTC10_2022`.

    .. math::

       \begin{equation}
          w_{p} = (h_{d} - h_{i}) - (\frac{T_{i} + T_{d}}{2}) (s_{d} - s_{i})
       \end{equation}

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol_sandberg_colby : pint.Quantity
       Polytropic head as described in :cite:`asmePTC10_2022` (J/kg).
    """
    Tm = (suc.T() + disch.T()) / 2
    h = (disch.h() - suc.h()) - Tm * (disch.s() - suc.s())
    return h


def eff_pol_sandberg_colby_multistep(suc, disch, disch_s=None):
    """Sandberg-Colby multistep polytropic efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.
    disch_s : ccp.State, optional
        Accepted for interface compatibility with the other polytropic
        methods (it is the scratch state passed by the point solver) and not
        used by this method.

    Returns
    -------
    eff_pol_sandberg_colby_multistep: pint.Quantity
        Sandberg-Colby multistep polytropic efficiency (dimensionless).
    """
    wp = head_pol_sandberg_colby_multistep(suc, disch)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


def head_pol_sandberg_colby_multistep(suc, disch, disch_s=None, nstep=10):
    r"""Polytropic head multistep method as described in section 5-2.4
    :cite:`asmePTC10_2022`.

    This implements the numerical integration method from ASME PTC 10-2022
    Figure 5-2.4-1 flowchart: the compression is split into ``nstep`` steps of
    equal pressure ratio, each step is a single-step Sandberg-Colby compression
    with the same polytropic efficiency, and that efficiency is the one for
    which the path ends at the measured discharge temperature. The number of
    steps is then increased by 5 until the efficiency changes by less than
    1e-5 (relative).

    The efficiency is found by a bracketed secant (:func:`ccp.roots.solve_monotone`)
    starting from the single-step Sandberg-Colby estimate; the path
    temperature decreases monotonically with the step efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.
    disch_s : ccp.State, optional
        Scratch state (the one passed by the point solver); a copy of
        ``disch`` is used when it is not given.
    nstep : int, optional
        Initial number of integration steps. Default is 10.

    Returns
    -------
    head_pol_sandberg_colby_multistep : pint.Quantity
        Polytropic head as described by :cite:`asmePTC10_2022` (J/kg).
    """
    T_d = disch.T().magnitude
    p_d = disch.p().magnitude
    dh = disch.h().magnitude - suc.h().magnitude
    work = _multistep_work_states(suc, disch_s)
    eff_est = _magnitude(eff_pol_sandberg_colby(suc, disch), "dimensionless")

    T_s = suc.T().magnitude

    def solve_level(n, guess):
        def residual(eff):
            return _multistep_path(suc, eff, p_d, n, work).T().magnitude - T_d

        # Newton first step: the temperature rise scales with 1/eff
        eff_0 = min(max(guess, 0.02), 0.999)
        r0 = residual(eff_0)
        eff_1 = eff_0 + r0 * eff_0 / max(r0 + T_d - T_s, 1e-3)
        return solve_monotone(
            residual,
            eff_0,
            lo=0.01,
            hi=1.0,
            increasing=False,
            x1=min(max(eff_1, 0.01), 1.0),
            f0=r0,
            rtol=1e-7,
            name="multistep polytropic efficiency",
        )

    eff, _ = _multistep_refine(solve_level, eff_est, nstep)
    return Q_(eff * dh, "joule/kilogram")


def head_pol_sandberg_colby_f(suc, disch, disch_s=None):
    r"""Polytropic head corrected by the :cite:`sandberg2013limitations` factor
    (original implementation).

    .. math::
       \begin{equation}
          H_{p_{s-c}} = f_{s-c} H_p
       \end{equation}

    Where :math:`f_{s-c}` is calculated by :py:func:`f_sandberg_colby` and
    :math:`H_p` is calculated by :py:func:`head_pol`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol_sandberg_colby_f : pint.Quantity
       Reference head as described by :cite:`sandberg2013limitations` (J/kg).
    """
    f = f_sandberg_colby(suc, disch)
    h = f * head_pol(suc, disch)
    return h


def eff_pol_sandberg_colby(suc, disch, disch_s=None):
    """Sandberg-Colby polytropic efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol_sandberg_colby: pint.Quantity
        Sandberg-Colby polytropic efficiency (dimensionless).
    """
    wp = head_pol_sandberg_colby(suc, disch)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


def eff_pol_sandberg_colby_f(suc, disch, disch_s=None):
    """Sandberg-Colby polytropic efficiency with correction factor."""
    wp = head_pol_sandberg_colby_f(suc, disch)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


def head_pol_huntington(suc, disch, disch_s=None):
    r"""Polytropic head calculated by the 3 point method described by
    :cite:`huntington1985`.

    The polytropic head in this case is calculated from the polytropic efficiency with:

    .. math::

       \begin{equation}
          \frac{1}{e} =
          1 +
          \frac{\frac{(s_d - s_s)}{R}}
          {a \ln(\frac{p_d}{p_s})
          + b((\frac{p_d}{p_s}) - 1)
          + \frac{c}{2}(\ln{(\frac{p_d}{p_s})})^2}
       \end{equation}

    The constants :math:`a`, :math:`b` and :math:`c` are calculated with:

    .. math::

       \begin{equation}
          a = z_s - b \\
          b = \frac{(z_s + z_d - 2z_{int})}{((\frac{p_s}{p_s})^{0.5} - 1)^2} \\
          c = \frac{(z_d - a - b(\frac{p_d}{p_s}))}{\ln{(\frac{p_d}{p_s})}}
       \end{equation}

    The intermediate values are calculated interactively:

    .. math::

       \begin{equation}
          p_{int} = \sqrt{p_s p_d} \\
          T_{int}' = T_{int} \exp{(\frac{(s_{int}' - s_{int})}{c_p})}
       \end{equation}

    And :math:`s_{int}` is calculated by:

    .. math::

       \begin{equation}
            s_{int}' = s_s + (s_d - s_s)
            \frac{\frac{a}{2}\ln{(\frac{p_d}{p_s})} + b((\frac{p_s}{p_s})^{0.5} - 1))
            + \frac{c}{8}(\ln{(\frac{p_d}{p_s})})^2}
            {a\ln(\frac{p_d}{p_s}) + b((\frac{p_d}{p_s})-1)
            + \frac{c}{2}(\ln(\frac{p_d}{p_s}))^2}
       \end{equation}

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol_huntington : pint.Quantity
       Polytropic head as described by :cite:`huntington1985` (J/kg).
    """
    eff = eff_pol_huntington(suc, disch)
    head = (disch.h() - suc.h()) * eff

    return head


def eff_pol_huntington(suc, disch, disch_s=None):
    """Polytropic efficiency calculated by the 3 point method described by
    :cite:`huntington1985`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol_huntington : pint.Quantity
       Polytropic efficiency as described by :cite:`huntington1985` (dimensionless).
    """
    p1 = suc.p()
    p2 = disch.p()
    s1 = suc.s()
    s2 = disch.s()
    z1 = suc.z()
    z2 = disch.z()
    T1 = suc.T()
    T2 = disch.T()
    p3 = np.sqrt(p1 * p2)

    T3 = np.sqrt(T1 * T2)
    error = 1
    n = 0
    if disch_s is None:
        state3 = State(p=p3, T=T3, fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
    else:
        state3 = disch_s
    while error > 1e-10:
        state3.update(p=p3, T=T3)
        s3 = state3.s()
        z3 = state3.z()
        cp3 = state3.cp()
        b = (z1 + z2 - 2 * z3) / (np.sqrt(p2 / p1) - 1) ** 2
        a = z1 - b
        c = (z2 - a - b * (p2 / p1)) / np.log(p2 / p1)
        s3_ = s1 + (s2 - s1) * (
            (
                ((a / 2) * np.log(p2 / p1))
                + b * (np.sqrt(p2 / p1) - 1)
                + (c / 8) * np.log(p2 / p1) ** 2
            )
            / (
                a * np.log(p2 / p1)
                + b * ((p2 / p1) - 1)
                + (c / 2) * np.log(p2 / p1) ** 2
            )
        )
        T3_new = T3 * np.exp((s3_ - s3) / cp3)
        error = abs(T3_new - T3).m
        T3 = T3_new

        n += 1
        if n == 100:
            raise RecursionError("Maximum number of iterations exceeded.")

    R = suc.gas_constant() / suc.molar_mass()
    inv_e = 1 + (
        ((s2 - s1) / R)
        / (a * np.log(p2 / p1) + b * ((p2 / p1) - 1) + (c / 2) * np.log(p2 / p1) ** 2)
    )
    eff = 1 / inv_e

    return eff


@check_units
def power_calc(flow_m, head, eff):
    """Calculate power.

    Parameters
    ----------
    flow_m : pint.Quantity, float
        Mass flow (kg/s).
    head : pint.Quantity, float
        Head (J/kg).
    eff : pint.Quantity, float
        Efficiency (dimensionless).

    Returns
    -------
    power : pint.Quantity
        Power (watt).
    """
    power = flow_m * head / eff

    return power.to("watt")


@check_units
def u_calc(D, speed):
    """Calculate the impeller tip speed.

    Parameters
    ----------
    D : float, pint.Quantity
        Impeller outer diameter (m).
    speed : pint.Quantity, float
        Impeller speed (rad/s).

    Returns
    -------
    u_calc : pint.Quantity
        Impeller tip speed (m/s).
    """
    u = speed * D / 2
    return u.to("m/s")


@check_units
def psi(head, speed, D):
    """Polytropic head coefficient.

    Parameters
    ----------
    head : pint.Quantity, float
        Polytropic head (J/kg).
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    D : float, pint.Quantity
        Impeller outer diameter (m).

    Returns
    -------
    psi : pint.Quantity
        Polytropic head coefficient (dimensionless).
    """
    u = u_calc(D, speed)
    psi = head / (u**2 / 2)
    return psi.to("dimensionless")


@check_units
def u_from_psi(head, psi):
    """Calculate u_calc from non dimensional psi.

    Parameters
    ----------
    head : pint.Quantity, float
        Polytropic head.
    psi : pint.Quantity, float
        Head coefficient.

    Returns
    -------
    u_calc : pint.Quantity, float
        Impeller tip speed.
    """
    u = np.sqrt(2 * head / psi)

    return u.to("m/s")


@check_units
def speed_from_psi(D, head, psi):
    """Calculate speed from non dimensional psi.

    Parameters
    ----------
    D : float, pint.Quantity
        Impeller outer diameter (m).
    head : pint.Quantity, float
        Polytropic head.
    psi : pint.Quantity, float
        Head coefficient.

    Returns
    -------
    u_calc : pint.Quantity, float
        Impeller tip speed.
    """
    u = u_from_psi(head, psi)

    speed = 2 * u / D

    return speed.to("rad/s")


@check_units
def phi(flow_v, speed, D):
    """Flow coefficient.

    Parameters
    ----------
    flow_v : float, pint.Quantity
        Impeller flow (m³/s).
    speed : float, pint.Quantity
        Impeller speed (rad/s).
    D : float, pint.Quantity
        Impeller outer diameter (m).

    Returns
    -------
    phi : pint.Quantity
        Flow coefficient (dimensionless).
    """
    u = u_calc(D, speed)

    phi = flow_v * 4 / (np.pi * D**2 * u)

    return phi.to("dimensionless")


@check_units
def flow_from_phi(D, phi, speed):
    """Calculate flow from non dimensional phi.

    Parameters
    ----------
    D : float, pint.Quantity
        Impeller outer diameter (m).
    phi : pint.Quantity, float
        Flow coefficient (m³/s).
    speed : pint.Quantity, float
        Speed (rad/s).

    Returns
    -------
    u_calc : pint.Quantity, float
        Impeller tip speed.
    """
    u = speed * D / 2

    flow_v = phi * (np.pi * D**2 * u) / 4

    return flow_v.to("m**3/s")


def head_from_psi(D, psi, speed):
    """Calculate head from non dimensional psi.

    Parameters
    ----------
    D : float, pint.Quantity
        Impeller outer diameter (m).
    psi : pint.Quantity, float
        Head coefficient.
    speed : pint.Quantity, float
        Speed (rad/s).

    Returns
    -------
    u_calc : pint.Quantity, float
        Impeller tip speed.
    """
    u = speed * D / 2
    head = psi * (u**2 / 2)

    return head.to("J/kg")


def _single_phase_solve(func):
    """Run a discharge closure with the imposed phase driving every flash.

    The closures below compute a compression discharge from the suction, so
    the single-phase root is the physical one (see
    :meth:`ccp.State.single_phase_solver`).
    """

    @wraps(func)
    def inner(*args, **kwargs):
        with State.single_phase_solver():
            return func(*args, **kwargs)

    return inner


def _magnitude(value, units):
    """SI magnitude of a pint quantity, or the value itself when it is a number."""
    if hasattr(value, "to"):
        return float(value.to(units).magnitude)
    return float(value)


def _kv(suc):
    """Suction isentropic volume exponent, guarded for the initial guesses."""
    k = float(suc.kv().magnitude)
    if not np.isfinite(k) or k <= 1.0:
        k = 1.3
    return k


def _polytropic_exponent(suc, eff):
    """``n/(n-1)`` of the ideal-gas polytropic path with efficiency ``eff``.

    Uses the suction isentropic exponent ``kv``: ``(n-1)/n = (k-1)/(k eff)``.
    Only used to seed the solvers; the brackets do not depend on it.
    """
    k = _kv(suc)
    return eff * k / (k - 1.0)


def _isentropic_T_at_rho(suc, disch, rho):
    """Temperature of the suction isentrope at density ``rho`` (kg/m3).

    Entropy increases monotonically with temperature at fixed volume
    (``ds/dT = cv/T``), so the root is bracketed and found with ``(rho, T)``
    inputs only: no flash iteration and no dependence on a previous state.
    ``disch`` is the reusable state that is updated in place.
    """
    s_s = suc.s().magnitude
    T_s = suc.T().magnitude
    rho_q = Q_(rho, "kg/m**3")
    T0 = T_s * (rho / suc.rho().magnitude) ** (_kv(suc) - 1.0)

    def residual(T):
        disch.update(rho=rho_q, T=Q_(T, "kelvin"))
        return disch.s().magnitude - s_s

    # Newton first step with ds/dT = cv/T at the guess
    r0 = residual(T0)
    T1 = T0 - r0 * T0 / max(disch.cv().magnitude, 1.0)
    T = solve_monotone(
        residual,
        T0,
        lo=0.1 * T_s,
        hi=10.0 * T_s,
        increasing=True,
        x1=T1,
        f0=r0,
        name="isentropic temperature at fixed density",
    )
    disch.update(rho=rho_q, T=Q_(T, "kelvin"))
    return T


def _isentropic_p_at_T(suc, disch, T):
    """Pressure of the suction isentrope at temperature ``T`` (K).

    Entropy decreases monotonically with pressure at fixed temperature
    (``ds/dp = -dv/dT``), so the root is bracketed and found with ``(p, T)``
    inputs only. ``disch`` is the reusable state that is updated in place.
    """
    s_s = suc.s().magnitude
    p_s = suc.p().magnitude
    T_s = suc.T().magnitude
    T_q = Q_(T, "kelvin")
    k = _kv(suc)
    p0 = p_s * (T / T_s) ** (k / (k - 1.0))

    def residual(p):
        disch.update(p=Q_(p, "Pa"), T=T_q)
        return s_s - disch.s().magnitude

    # Newton first step with ds/dp = -v/T (ideal gas) at the guess
    r0 = residual(p0)
    p1 = p0 * (1.0 - r0 * T * disch.rho().magnitude / p0)
    p = solve_monotone(
        residual,
        p0,
        lo=1e-3 * p_s,
        hi=1e3 * p_s,
        increasing=True,
        x1=p1,
        f0=r0,
        name="isentropic pressure at fixed temperature",
    )
    disch.update(p=Q_(p, "Pa"), T=T_q)
    return p


def _solve_T_at_p_for_eff(
    suc, disch, scratch, p_d, eff, eff_calc_func, name, T_guess=None
):
    """Update ``disch`` in place to the state at ``p_d`` (Pa) whose polytropic
    efficiency from ``suc`` equals ``eff``; returns its temperature (K).

    The isentropic state at ``p_d`` is the lower end of the temperature
    bracket (efficiency 1); the efficiency decreases monotonically above it.
    Without ``T_guess`` the initial guess scales the real isentropic head with
    the ideal-gas ratio of polytropic to isentropic head and converts it to a
    temperature with one (p, h) flash.

    With ``T_guess`` (the steps of the multistep path, seeded from the
    previous step) the isentropic state is not computed first: for a
    near-ideal gas the efficiency also decreases monotonically from above 1
    between the suction temperature and the isentropic one, so the suction
    temperature closes the bracket. When that fails (dense gas below its
    inversion temperature, where the enthalpy falls with pressure at constant
    temperature) the solve is repeated from the isentropic state.
    """
    p_d_q = Q_(p_d, "Pa")
    h_s = suc.h().magnitude
    p_s = suc.p().magnitude
    T_s = suc.T().magnitude
    if p_d <= p_s:
        raise ValueError(
            f"discharge pressure {p_d} Pa is not above the suction pressure {p_s} Pa"
        )

    if T_guess is not None:
        try:
            return _solve_T_at_p_for_eff_from(
                suc, disch, scratch, p_d_q, eff, eff_calc_func, name, T_s, T_guess
            )
        except ValueError:
            pass

    disch.update(p=p_d_q, s=suc.s())
    T_isen = disch.T().magnitude
    head_isen = disch.h().magnitude - h_s

    k = _kv(suc)
    nn = _polytropic_exponent(suc, eff)
    r = p_d / p_s
    if r > 1.0 and head_isen > 0.0:
        ratio = (nn * (r ** (1.0 / nn) - 1.0)) / (
            (k / (k - 1.0)) * (r ** ((k - 1.0) / k) - 1.0)
        )
    else:
        ratio = 1.0
    try:
        disch.update(p=p_d_q, h=Q_(h_s + ratio * head_isen / eff, "joule/kilogram"))
        T0 = disch.T().magnitude
    except ValueError:
        T0 = 1.05 * T_isen
    return _solve_T_at_p_for_eff_from(
        suc, disch, scratch, p_d_q, eff, eff_calc_func, name, T_isen, T0
    )


def _solve_T_at_p_for_eff_from(
    suc, disch, scratch, p_d_q, eff, eff_calc_func, name, T_lo, T0
):
    """Efficiency solve on ``T`` in ``[T_lo, 10 T_lo]`` from the guess ``T0``.

    The first solver step is a Newton step with the slope
    ``d(eff)/dT = -1/(T - T_s)`` of the ideal-gas polytropic efficiency.
    """
    T_s = suc.T().magnitude
    T0 = max(T0, T_lo * (1.0 + 1e-6))

    def residual(T):
        disch.update(p=p_d_q, T=Q_(T, "kelvin"))
        return _magnitude(eff_calc_func(suc, disch, scratch), "dimensionless") - eff

    r0 = residual(T0)
    T1 = max(T0 + r0 * (T0 - T_s), T_lo * (1.0 + 1e-6))
    T = solve_monotone(
        residual,
        T0,
        lo=T_lo,
        hi=10.0 * T_lo,
        increasing=False,
        x1=T1,
        f0=r0,
        name=name,
    )
    disch.update(p=p_d_q, T=Q_(T, "kelvin"))
    return T


def _multistep_work_states(suc, scratch=None):
    """Three reusable states for the multistep path integration."""
    a = State(p=suc.p(), T=suc.T(), fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
    b = copy(a)
    if scratch is None:
        scratch = copy(a)
    return [a, b, scratch]


def _multistep_path(suc, eff, p_d, nstep, work):
    """March the constant-efficiency Sandberg-Colby path from ``suc`` to ``p_d``.

    Each of the ``nstep`` steps has the same pressure ratio and the same
    single-step Sandberg-Colby efficiency ``eff`` (ASME PTC 10-2022 Fig.
    5-2.4-1). The three states in ``work`` are updated in place and the state
    at ``p_d`` is returned (it is one of them). Each step is seeded with the
    temperature ratio of the previous one (the steps are nearly identical);
    the first with the polytropic estimate from the isentropic temperature
    exponent.
    """
    a, b, scratch = work
    a.update(p=suc.p(), T=suc.T())
    p_s = suc.p().magnitude
    rp = (p_d / p_s) ** (1.0 / nstep)
    kT = float(suc.kT().magnitude)
    if not np.isfinite(kT) or kT <= 1.0:
        kT = _kv(suc)
    ratio = rp ** ((kT - 1.0) / (kT * eff))
    p_j = p_s
    for j in range(nstep):
        p_j = p_d if j == nstep - 1 else p_j * rp
        T_in = a.T().magnitude
        T_out = _solve_T_at_p_for_eff(
            a,
            b,
            scratch,
            p_j,
            eff,
            eff_pol_sandberg_colby,
            "multistep step",
            T_guess=T_in * ratio,
        )
        ratio = T_out / T_in
        a, b = b, a
    work[0], work[1] = a, b
    return a


def _multistep_refine(solve_level, guess, nstep=10, rtol=1e-5, max_steps=200):
    """ASME PTC 10-2022 step refinement around a solve at fixed step count.

    ``solve_level(nstep, guess)`` returns the solution with ``nstep`` steps;
    the count grows by 5 until two consecutive solutions agree to ``rtol``.
    Returns the solution and the final step count.
    The refinement is applied outside the root solve so that each level's
    residual is a smooth function of its variable.
    """
    previous = None
    x = guess
    while True:
        x = solve_level(nstep, x)
        if previous is not None and abs(x - previous) <= rtol * abs(x):
            return x, nstep
        previous = x
        nstep += 5
        if nstep > max_steps:
            raise ValueError(
                "multistep refinement did not converge within "
                f"{max_steps} steps (last change {abs(x - previous) / abs(x):.2e})"
            )


def _multistep_disch_from_disch_p_eff(suc, p_d, eff):
    work = _multistep_work_states(suc)
    h_s = suc.h().magnitude

    def solve_level(n, guess):
        return _multistep_path(suc, eff, p_d, n, work).h().magnitude - h_s

    _, n = _multistep_refine(solve_level, None)
    return _multistep_path(suc, eff, p_d, n, work)


def _multistep_disch_from_head_eff(suc, head, eff):
    work = _multistep_work_states(suc)
    h_s = suc.h().magnitude
    p_s = suc.p().magnitude
    h_d = h_s + head / eff
    p_isen = _isentropic_p_at_h(suc, work[2], h_d)
    # the single-step Sandberg-Colby solution is within about 1e-3 of the
    # multistep one: start there
    p0 = disch_from_suc_head_eff(suc, head, eff, "sandberg_colby").p().magnitude

    def solve_level(n, guess):
        def residual(p):
            return _multistep_path(suc, eff, p, n, work).h().magnitude - h_d

        # Newton first step with dh/dp = v at the end of the path
        r0 = residual(guess)
        p_1 = guess - r0 * work[0].rho().magnitude
        return solve_monotone(
            residual,
            guess,
            lo=p_s,
            hi=p_isen,
            increasing=True,
            x1=p_1,
            f0=r0,
            rtol=1e-7,
            name="multistep head and efficiency closure",
        )

    p, n = _multistep_refine(solve_level, p0)
    return _multistep_path(suc, eff, p, n, work)


def _multistep_disch_from_disch_T_head(suc, T_d, head):
    work = _multistep_work_states(suc)
    h_s = suc.h().magnitude
    p_s = suc.p().magnitude
    T_d_q = Q_(T_d, "kelvin")
    probe = State(p=suc.p(), T=T_d_q, fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
    p_isen = _isentropic_p_at_T(suc, probe, T_d)
    # start from the single-step Sandberg-Colby solution
    p0 = disch_from_suc_disch_T_head(suc, T_d, head, "sandberg_colby").p().magnitude

    def solve_level(n, guess):
        def residual(p):
            probe.update(p=Q_(p, "Pa"), T=T_d_q)
            eff = head / (probe.h().magnitude - h_s)
            eff = min(max(eff, 0.01), 1.0)
            return _multistep_path(suc, eff, p, n, work).T().magnitude - T_d

        # Newton first step with dT/dp = T (n-1)/n / p of the polytropic path
        r0 = residual(guess)
        probe.update(p=Q_(guess, "Pa"), T=T_d_q)
        eff_0 = min(max(head / (probe.h().magnitude - h_s), 0.01), 1.0)
        p_1 = guess - r0 * guess * _polytropic_exponent(suc, eff_0) / T_d
        return solve_monotone(
            residual,
            guess,
            lo=min(p_s, p_isen),
            hi=max(p_s, p_isen),
            increasing=True,
            x1=p_1,
            f0=r0,
            rtol=1e-7,
            name="multistep discharge temperature and head closure",
        )

    p, _ = _multistep_refine(solve_level, p0)
    probe.update(p=Q_(p, "Pa"), T=T_d_q)
    return probe


def _multistep_disch_from_volume_ratio_eff(suc, volume_ratio, eff):
    work = _multistep_work_states(suc)
    p_s = suc.p().magnitude
    rho_d = suc.rho().magnitude * volume_ratio
    # start from the single-step Sandberg-Colby solution: the density along
    # the path is not monotone in the discharge pressure for near-critical
    # compressions that end below the suction density, and the single-step
    # solution sits on the right branch
    p0 = (
        disch_from_suc_volume_ratio_eff(suc, volume_ratio, eff, "sandberg_colby")
        .p()
        .magnitude
    )

    def solve_level(n_steps, guess):
        def residual(p):
            return _multistep_path(suc, eff, p, n_steps, work).rho().magnitude - rho_d

        # the direction of the residual around the seed decides the branch
        # (the path density can decrease with pressure near the critical
        # point): two evaluations that the solver reuses
        guess_1 = guess * 1.001
        r0, r1 = residual(guess), residual(guess_1)
        return solve_monotone(
            residual,
            guess,
            lo=p_s,
            hi=1e3 * p_s,
            increasing=r1 > r0,
            x1=guess_1,
            f0=r0,
            f1=r1,
            rtol=1e-7,
            name="multistep volume ratio closure",
        )

    p, n = _multistep_refine(solve_level, p0)
    return _multistep_path(suc, eff, p, n, work)


def _isentropic_p_at_h(suc, disch, h):
    """Pressure of the suction isentrope at enthalpy ``h`` (J/kg).

    Enthalpy increases monotonically with pressure at fixed entropy
    (``dh/dp = v``), so the root is bracketed and found with ``(p, s)``
    flashes only; CoolProp's ``(h, s)`` flash is unreliable for mixtures on
    the HEOS backend. ``disch`` is the reusable state that is updated in
    place.
    """
    s_s = suc.s()
    p_s = suc.p().magnitude
    h_s = suc.h().magnitude
    k = _kv(suc)
    kk = k / (k - 1.0)
    pv = p_s / suc.rho().magnitude
    p0 = p_s * max(1.0 + (h - h_s) / (kk * pv), 1e-3) ** kk

    def residual(p):
        disch.update(p=Q_(p, "Pa"), s=s_s)
        return disch.h().magnitude - h

    # Newton first step with dh/dp = v at the guess
    r0 = residual(p0)
    p1 = p0 - r0 * disch.rho().magnitude
    p = solve_monotone(
        residual,
        p0,
        lo=1e-3 * p_s,
        hi=1e3 * p_s,
        increasing=True,
        x1=p1,
        f0=r0,
        name="isentropic pressure at fixed enthalpy",
    )
    disch.update(p=Q_(p, "Pa"), s=s_s)
    return p


@_single_phase_solve
def isentropic_disch_from_rho(suc, disch_rho):
    """Discharge state of an isentropic compression to a target density.

    The state is found on the suction isentrope with ``(rho, T)`` inputs (see
    :func:`_isentropic_T_at_rho`) rather than with a ``(rho, s)`` flash: for
    dense fluids that flash has two roots, the physical compression and a cold
    root below the suction pressure, and which one it returns depends on the
    backend's internal state.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch_rho : pint.Quantity
        Target discharge density.

    Returns
    -------
    disch : ccp.State
        Discharge state of the isentropic compression to ``disch_rho``.
    """
    rho = _magnitude(disch_rho, "kg/m**3")
    disch = State(
        rho=Q_(rho, "kg/m**3"), T=suc.T(), fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase
    )
    _isentropic_T_at_rho(suc, disch, rho)
    return disch


@_single_phase_solve
def disch_from_suc_rho_eff(suc, disch_rho, eff, eff_calc_func):
    """Discharge at a fixed density matching a polytropic efficiency.

    Temperature is the iteration variable. For a compression (discharge
    density above the suction density) the polytropic efficiency is 1 at the
    isentropic temperature and decreases monotonically as the temperature
    rises at constant density, so the root is bracketed from the isentropic
    state upwards. Below the isentropic temperature the efficiency is
    meaningless (negative or singular for dense fluids), which is why no
    iterate is allowed there.

    Near the critical point a compression can end at a density *below* the
    suction density (dense ethylene from 86 to 137 bar in the Evans and Huble
    2017 set). The isentrope is then an expansion, the enthalpy rise is
    negative at the isentropic state and the efficiency is singular where it
    crosses zero. The physical branch starts just above that temperature; the
    efficiency there rises from below, and the root closest to the start of
    the branch (the smallest temperature rise) is returned.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch_rho : pint.Quantity
        Target discharge density.
    eff : pint.Quantity, float
        Target polytropic efficiency.
    eff_calc_func : callable
        ``eff_calc_func(suc, disch, disch_s)`` returning the polytropic
        efficiency; ``disch_s`` is a scratch state.

    Returns
    -------
    disch : ccp.State
        Discharge state.
    """
    rho = _magnitude(disch_rho, "kg/m**3")
    eff = _magnitude(eff, "dimensionless")
    rho_q = Q_(rho, "kg/m**3")
    disch = isentropic_disch_from_rho(suc, disch_rho)
    scratch = copy(disch)
    h_s = suc.h().magnitude
    T_lo = disch.T().magnitude

    if disch.h().magnitude - h_s <= 0.0:
        # expansion isentrope: start the branch where the enthalpy rise
        # turns positive (enthalpy increases with T at fixed volume)
        def dh(T):
            disch.update(rho=rho_q, T=Q_(T, "kelvin"))
            return disch.h().magnitude - h_s

        T_h = solve_monotone(
            dh,
            1.01 * T_lo,
            lo=T_lo,
            hi=10.0 * T_lo,
            increasing=True,
            name="zero enthalpy rise at fixed density",
        )
        T_lo = T_h * (1.0 + 1e-3)

    def residual(T):
        disch.update(rho=rho_q, T=Q_(T, "kelvin"))
        return _magnitude(eff_calc_func(suc, disch, scratch), "dimensionless") - eff

    # ideal-gas polytropic path p v^n = const with (n-1)/n = (k-1)/(k eff)
    k = _kv(suc)
    n_minus_1 = (k - 1.0) / max(k * eff - (k - 1.0), 1e-3)
    T0 = suc.T().magnitude * (rho / suc.rho().magnitude) ** n_minus_1
    T0 = max(T0, T_lo * (1.0 + 1e-6))

    T_s = suc.T().magnitude
    r_lo = residual(T_lo)
    if r_lo < 0.0:
        # rising branch (see above): search upwards from the branch start
        increasing, x0, x1, r0 = True, T_lo, 1.05 * T_lo, r_lo
    else:
        # Newton first step with the ideal-gas slope d(eff)/dT = -1/(T - T_s)
        r0 = residual(T0)
        increasing, x0, x1 = False, T0, max(T0 + r0 * (T0 - T_s), T_lo)

    T = solve_monotone(
        residual,
        x0,
        lo=T_lo,
        hi=10.0 * T_lo,
        increasing=increasing,
        x1=x1,
        f0=r0,
        name="efficiency at fixed density (volume ratio closure)",
    )
    disch.update(rho=rho_q, T=Q_(T, "kelvin"))
    return disch


@_single_phase_solve
def disch_from_suc_volume_ratio_eff(suc, volume_ratio, eff, polytropic_method=None):
    """Calculate discharge state from suction, volume ratio and efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    volume_ratio : pint.Quantity, float
        Ratio between suction and discharge specific volumes (v_s / v_d).
    eff : pint.Quantity, float
        Polytropic efficiency (dimensionless).

    Returns
    -------
    disch : ccp.State
        Discharge state.
    """
    if polytropic_method is None:
        polytropic_method = ccp.config.POLYTROPIC_METHOD
    if polytropic_method == "sandberg_colby_multistep":
        return _multistep_disch_from_volume_ratio_eff(
            suc,
            _magnitude(volume_ratio, "dimensionless"),
            _magnitude(eff, "dimensionless"),
        )
    eff_calc_func = globals()[f"eff_pol_{polytropic_method}"]
    disch_rho = suc.rho() * _magnitude(volume_ratio, "dimensionless")
    return disch_from_suc_rho_eff(suc, disch_rho, eff, eff_calc_func)


@_single_phase_solve
def disch_from_suc_head_eff(suc, head, eff, polytropic_method=None):
    """Calculate discharge state from suction, head and efficiency.

    The discharge enthalpy is fixed by ``h_d = h_s + head / eff``; pressure is
    the iteration variable along that isenthalp. The polytropic head is zero
    at the suction pressure and equals ``h_d - h_s`` at the isentropic
    pressure, and increases monotonically in between, so the root is
    bracketed by those two states. The initial guess is the ideal-gas
    polytropic pressure for the suction isentropic exponent.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    head : pint.Quantity, float
        Polytropic head (J/kg).
    eff : pint.Quantity, float
        Polytropic efficiency (dimensionless).

    Returns
    -------
    disch : ccp.State
        Discharge state.
    """
    if polytropic_method is None:
        polytropic_method = ccp.config.POLYTROPIC_METHOD
    if polytropic_method == "sandberg_colby_multistep":
        return _multistep_disch_from_head_eff(
            suc, _magnitude(head, "joule/kilogram"), _magnitude(eff, "dimensionless")
        )

    head_calc_func = globals()[f"head_pol_{polytropic_method}"]
    head = _magnitude(head, "joule/kilogram")
    eff = _magnitude(eff, "dimensionless")
    h_s = suc.h().magnitude
    h_disch = Q_(h_s + head / eff, "joule/kilogram")

    # isentropic compression to h_disch: upper end of the pressure bracket
    disch = State(p=suc.p(), T=suc.T(), fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
    p_isen = _isentropic_p_at_h(suc, disch, h_disch.magnitude)
    p_s = suc.p().magnitude

    nn = _polytropic_exponent(suc, eff)
    pv = p_s / suc.rho().magnitude
    p0 = p_s * (1.0 + head / (nn * pv)) ** nn

    scratch = copy(disch)

    def residual(p):
        disch.update(h=h_disch, p=Q_(p, "Pa"))
        return _magnitude(head_calc_func(suc, disch, scratch), "joule/kilogram") - head

    # Newton first step with d(head)/dp = v_d (isenthalpic: ds/dp = -v/T)
    p0 = min(max(p0, p_s * (1.0 + 1e-9)), p_isen)
    r0 = residual(p0)
    p1 = p0 - r0 * disch.rho().magnitude
    p = solve_monotone(
        residual,
        p0,
        lo=p_s,
        hi=p_isen,
        increasing=True,
        x1=p1,
        f0=r0,
        name="head at fixed enthalpy (head and efficiency closure)",
    )
    disch.update(h=h_disch, p=Q_(p, "Pa"))
    return disch


@_single_phase_solve
def disch_from_suc_disch_p_eff(suc, disch_p, eff, polytropic_method=None):
    """Calculate discharge state from suction, discharge pressure and efficiency.

    Temperature is the iteration variable at the fixed discharge pressure: the
    polytropic efficiency is 1 at the isentropic temperature and decreases
    monotonically above it, so the root is bracketed from the isentropic state
    upwards. The initial guess scales the real isentropic head with the
    ideal-gas ratio of polytropic to isentropic head.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch_p : pint.Quantity, float
        Discharge pressure (Pa).
    eff : pint.Quantity, float
        Polytropic efficiency (dimensionless).

    Returns
    -------
    disch : ccp.State
        Discharge state.
    """
    if polytropic_method is None:
        polytropic_method = ccp.config.POLYTROPIC_METHOD
    if polytropic_method == "sandberg_colby_multistep":
        return _multistep_disch_from_disch_p_eff(
            suc, _magnitude(disch_p, "Pa"), _magnitude(eff, "dimensionless")
        )

    eff_calc_func = globals()[f"eff_pol_{polytropic_method}"]
    disch = State(p=disch_p, T=suc.T(), fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
    scratch = copy(disch)
    _solve_T_at_p_for_eff(
        suc,
        disch,
        scratch,
        _magnitude(disch_p, "Pa"),
        _magnitude(eff, "dimensionless"),
        eff_calc_func,
        "efficiency at fixed pressure (discharge pressure closure)",
    )
    return disch


@_single_phase_solve
def disch_from_suc_disch_T_head(suc, disch_T, head, polytropic_method=None):
    """Calculate discharge state from suction, discharge temperature and head.

    Pressure is the iteration variable at the fixed discharge temperature: the
    polytropic head increases monotonically with pressure, from about zero at
    the suction pressure to the enthalpy rise at the isentropic pressure, so
    the root is bracketed by those two states.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch_T : pint.Quantity, float
        Discharge temperature (degK).
    head : pint.Quantity, float
        Polytropic head (J/kg).

    Returns
    -------
    disch : ccp.State
        Discharge state.
    """
    if polytropic_method is None:
        polytropic_method = ccp.config.POLYTROPIC_METHOD
    if polytropic_method == "sandberg_colby_multistep":
        return _multistep_disch_from_disch_T_head(
            suc, _magnitude(disch_T, "kelvin"), _magnitude(head, "joule/kilogram")
        )

    head_calc_func = globals()[f"head_pol_{polytropic_method}"]
    head = _magnitude(head, "joule/kilogram")
    T_d = _magnitude(disch_T, "kelvin")
    T_d_q = Q_(T_d, "kelvin")
    p_s = suc.p().magnitude
    T_s = suc.T().magnitude

    disch = State(p=suc.p(), T=T_d_q, fluid=suc.fluid, EOS=suc.EOS, phase=suc.phase)
    p_isen = _isentropic_p_at_T(suc, disch, T_d)

    # initial guess: ideal-gas polytropic path through (T_s, p_s) and T_d with
    # the exponent that reproduces the head
    tau = T_d / T_s
    pv = p_s / suc.rho().magnitude
    if tau > 1.0 and head > 0.0:
        p0 = p_s * tau ** (head / (pv * (tau - 1.0)))
    else:
        p0 = 0.5 * (p_s + p_isen)

    scratch = copy(disch)

    def residual(p):
        disch.update(p=Q_(p, "Pa"), T=T_d_q)
        return _magnitude(head_calc_func(suc, disch, scratch), "joule/kilogram") - head

    # Newton first step with d(head)/dp = v_d (isothermal: ds/dp = -dv/dT)
    lo, hi = min(p_s, p_isen), max(p_s, p_isen)
    p0 = min(max(p0, lo), hi)
    r0 = residual(p0)
    p1 = p0 - r0 * disch.rho().magnitude
    p = solve_monotone(
        residual,
        p0,
        lo=lo,
        hi=hi,
        increasing=True,
        x1=p1,
        f0=r0,
        name="head at fixed temperature (discharge temperature closure)",
    )
    disch.update(p=Q_(p, "Pa"), T=T_d_q)
    return disch


@check_units
def reynolds(suc, speed, b, D):
    """Calculate the Reynolds number.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    b : float, pint.Quantity
        Impeller width at the outer blade diameter (m).
    D : float, pint.Quantity
        Impeller outer diameter (m).

    Returns
    -------
    reynolds : pint.Quantity
        Reynolds number (dimensionless).
    """
    u = u_calc(D, speed)
    re = u * b * suc.rho() / suc.viscosity()

    return re.to("dimensionless")


@check_units
def mach(suc, speed, D):
    """Calculate the Mach number.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    D : float, pint.Quantity
        Impeller outer diameter (m).

    Returns
    -------
    mach : pint.Quantity
        Mach number (dimensionless).
    """
    u = u_calc(D, speed)
    a = suc.speed_sound()
    ma = u / a

    return ma.to("dimensionless")


def correct_reynolds_1997(suc, speed, original_point):
    """Correct the efficiency based on ASME PTC 10 1997.

    Parameters
    ----------
    suc : ccp.State
        New suction state.
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    original_point : ccp.Point
        Original operating point.

    Returns
    -------
    rem_corr_eff, rem_corr_psi, rem_corr_phi
        Correction factors for eff, psi and phi.
    """
    rc_original = 0.988 / original_point.reynolds**0.243
    rb_original = np.log(0.000125 + 13.67 / original_point.reynolds) / np.log(
        original_point.surface_roughness.to("in").m + (13.67 / original_point.reynolds)
    )
    ra_original = (
        0.066
        + 0.934
        * ((4.8e6 * original_point.b.to("ft").m) / original_point.reynolds)
        ** rc_original
    )
    reynolds_converted = reynolds(
        suc=suc, speed=speed, b=original_point.b, D=original_point.D
    )
    rc_converted = 0.988 / reynolds_converted**0.243
    rb_converted = np.log(0.000125 + 13.67 / reynolds_converted) / np.log(
        original_point.surface_roughness.to("in").m + (13.67 / reynolds_converted)
    )
    ra_converted = (
        0.066
        + 0.934
        * ((4.8e6 * original_point.b.to("ft").m) / reynolds_converted) ** rc_converted
    )

    eff_converted = 1 - (1 - original_point.eff) * (ra_converted / ra_original) * (
        rb_converted / rb_original
    )

    rem_corr_eff = rem_corr_psi = eff_converted / original_point.eff
    rem_corr_phi = 1

    return rem_corr_eff, rem_corr_psi, rem_corr_phi


def correct_reynolds_2022(suc, speed, original_point):
    """Correct efficiency, head coefficient and flow coefficient based on ASME
    PTC 10 2022.

    Parameters
    ----------
    suc : ccp.State
        New suction state.
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    original_point : ccp.Point
        Original operating point.

    Returns
    -------
    rem_corr_eff, rem_corr_psi, rem_corr_phi
        Correction factors for eff, psi and phi.

    """
    ra = original_point.surface_roughness
    reynolds_converted = reynolds(
        suc=suc, speed=speed, b=original_point.b, D=original_point.D
    )

    lambda_inf = (
        1.74 - 2 * np.log10(2 * original_point.surface_roughness / original_point.b)
    ) ** (-2)

    def colebrook(lamda, reynolds):
        return (
            1 / np.sqrt(lamda)
            + 2
            * np.log10(
                1 + (18.7 * original_point.b) / (reynolds * 2 * ra * np.sqrt(lamda))
            )
            - 1 / np.sqrt(lambda_inf)
        )

    lambda_t = newton(colebrook, x0=lambda_inf, args=(original_point.reynolds,))
    lambda_sp = newton(colebrook, x0=lambda_inf, args=(reynolds_converted,))

    rem_corr_eff = 1 / original_point.eff + (1 - 1 / original_point.eff) * (
        (0.3 + 0.7 * lambda_sp / lambda_inf) / (0.3 + 0.7 * lambda_t / lambda_inf)
    )
    rem_corr_psi = 0.5 + 0.5 * rem_corr_eff
    rem_corr_phi = np.sqrt(rem_corr_psi)

    return rem_corr_eff, rem_corr_psi, rem_corr_phi
