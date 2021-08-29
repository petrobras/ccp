from copy import copy
from warnings import warn

import CoolProp.CoolProp as CP
import numpy as np
import ccp.config
from scipy.optimize import newton
from plotly import graph_objects as go
from . import _RP

from . import Q_
from .config.fluids import get_name, normalize_mix
from .config.units import check_units


class State(CP.AbstractState):
    """A thermodynamic state.

    .. note::
        To create a state use State.define(...)


    This class is inherited from CP.AbstractState.
    Some extra functionality has been added.


    Creates a state from fluid composition and two properties.
    Properties can be floats (SI units are considered) or pint quantities.

    Parameters
    ----------
    p : float, pint.Quantity
        Pressure
    T : float, pint.Quantity
        Temperature
    h : float, pint.Quantity
        Enthalpy
    s : float, pint.Quantity
        Entropy
    rho : float, pint.Quantity
        Specific mass

    fluid : dict
        Dictionary with constituent and composition.
        (e.g.: ({'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092})
    EOS : string
        String with HEOS or REFPROP

    Returns
    -------
    state : State object

    Examples
    --------
    >>> import ccp
    >>> Q_ = ccp.Q_
    >>> fluid = {'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092}
    >>> s = ccp.State.define(p=101008, T=273, fluid=fluid)
    >>> s.rho()
    <Quantity(1.28939426, 'kilogram / meter ** 3')>
    >>> # Using pint quantities
    >>> s = ccp.State.define(fluid=fluid, p=Q_(1, 'atm'), T=Q_(0, 'degC'))
    >>> s.h()
    <Quantity(273291.7, 'joule / kilogram')>
    """

    def __init__(self, EOS, _fluid):
        # no call to super(). see :
        # http://stackoverflow.com/questions/18260095/
        self.EOS = EOS
        self._fluid = _fluid

    def __repr__(self):
        args = {k: v for k, v in self.init_args.items() if v is not None}
        args_repr = [f'{k}=Q_("{getattr(self, k)():.0f~P}")' for k, v in args.items()]
        args_repr = ", ".join(args_repr)

        fluid_dict = self.fluid
        sorted_fluid_keys = sorted(fluid_dict, key=fluid_dict.get, reverse=True)
        fluid_repr = [f'"{k}": {fluid_dict[k]:.5f}' for k in sorted_fluid_keys]
        fluid_repr = "fluid={" + ", ".join(fluid_repr) + "}"

        return "State.define(" + args_repr + ", " + fluid_repr + ")"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            self_fluid_rounded = {k: round(v, 3) for k, v in self.fluid.items()}
            other_fluid_rounded = {k: round(v, 3) for k, v in other.fluid.items()}
            if (
                self_fluid_rounded == other_fluid_rounded
                and np.allclose(self.p(), other.p(), rtol=1e-3)
                and np.allclose(self.T(), other.T(), rtol=1e-3)
            ):
                return True
        return False

    def _fluid_dict(self):
        # preserve the dictionary from define method
        fluid_dict = {}
        for k, v in zip(self.fluid_names(), self.get_mole_fractions()):
            fluid_dict[k] = v
            self.fluid = fluid_dict
        return fluid_dict

    def gas_constant(self, units=None):
        """Gas constant in joule / (mol kelvin).

        Returns
        -------
        gas_constant : pint.Quantity
            Gas constant (joule / (mol kelvin).
        """
        gas_constant = Q_(super().gas_constant(), "joule / (mol kelvin)")
        if units:
            gas_constant = gas_constant.to(units)
        return gas_constant

    def molar_mass(self, units=None):
        """Molar mass in kg/mol.

        Returns
        -------
        molar_mass : pint.Quantity
            Molar mass (kg/mol).
        """
        molar_mass = Q_(super().molar_mass(), "kg/mol")
        if units:
            molar_mass = molar_mass.to(units)
        return molar_mass

    def T(self, units=None):
        """Temperature in Kelvin.

        Returns
        -------
        T : pint.Quantity
            Temperature (Kelvin).
        """
        T = Q_(super().T(), "kelvin")
        if units:
            T = T.to(units)
        return T

    def p(self, units=None):
        """Pressure in Pascal.

        Returns
        -------
        p : pint.Quantity
            Pressure (pascal).
        """
        p = Q_(super().p(), "pascal")
        if units:
            p = p.to(units)
        return p

    def cp(self, units=None):
        """Specific heat at constant pressure joule/(kilogram kelvin).

        Returns
        -------
        cp : pint.Quantity
            Specific heat at constant pressure joule/(kilogram kelvin).
        """
        cp = Q_(super().cpmass(), "joule/(kilogram kelvin)")
        # use REFPROP directly with forced gas condition if cp value does not converge
        if cp < 0:
            fluids = self._fluid.replace("&", "*")
            r = _RP.REFPROPdll(
                fluids,
                "PTV",
                "Cp",
                _RP.MASS_BASE_SI,
                0,
                0,
                self.p("kPa").m,
                self.T().m,
                self.get_mole_fractions(),
            )
            cp = Q_(r.Output[0], "joule/(kilogram kelvin)")

        if units:
            cp = cp.to(units)
        return cp

    def cv(self, units=None):
        """Specific heat at constant volume joule/(kilogram kelvin).

        Returns
        -------
        cv : pint.Quantity
            Specific heat at constant volume joule/(kilogram kelvin).
        """
        cv = Q_(super().cvmass(), "joule/(kilogram kelvin)")
        if units:
            cv = cv.to(units)
        return cv

    def h(self, units=None):
        """Specific Enthalpy (joule/kilogram).

        Returns
        -------
        h : pint.Quantity
            Enthalpy (joule/kilogram).
        """
        h = Q_(super().hmass(), "joule/kilogram")
        if units:
            h = h.to(units)
        return h

    def s(self, units=None):
        """Specific entropy (per unit of mass).

        Returns
        -------
        s : pint.Quantity
            Entropy (joule/(kelvin kilogram)).
        """
        s = Q_(super().smass(), "joule/(kelvin kilogram)")
        if units:
            s = s.to(units)
        return s

    def p_critical(self, units=None):
        """Critical Pressure in Pa.

        Returns
        -------
        p_critical : pint.Quantity
            Critical pressure (Pa).
        """
        p_critical = Q_(super().p_critical(), "Pa")
        if units:
            p_critical = p_critical.to(units)
        return p_critical

    def T_critical(self, units=None):
        """Critical Temperature in K.

        Returns
        -------
        T_critical : pint.Quantity
            Critical temperature (degK).
        """
        T_critical = Q_(super().T_critical(), "K")
        if units:
            T_critical.to(units)
        return T_critical

    def rho(self, units=None):
        """Specific mass (kilogram/m**3).

        Returns
        -------
        rho : pint.Quantity
            Specific mass (kilogram/m**3).
        """
        rho = Q_(super().rhomass(), "kilogram/m**3")
        if units:
            rho = rho.to(units)
        return rho

    def v(self, units=None):
        """Specific volume (m**3/kilogram).

        Returns
        -------
        v : pint.Quantity
            Specific volume (m**3/kilogram).
        """
        v = 1 / self.rho()
        if units:
            v = (1 / self.rho()).to(units)
        return v

    def z(self, units=None):
        """Compressibility (dimensionless).

        Returns
        -------
        z : pint.Quantity
            Compressibility (dimensionless).
        """
        z = self.p() * self.molar_mass() / (self.rho() * self.gas_constant() * self.T())
        return z.to("dimensionless")

    def speed_sound(self, units=None):
        """Speed of sound - Eq. 8.1 from P. Nederstigt - Real Gas Thermodynamics.

        Returns
        -------
        speed_sound : pint.Quantity
            Speed of sound (m/s).
        """
        speed_sound = Q_(
            np.sqrt(self.first_partial_deriv(CP.iP, CP.iDmass, CP.iSmass)), "m/s"
        )
        if units:
            speed_sound = speed_sound.to(units)
        return speed_sound

    def viscosity(self, units=None):
        """Viscosity in pascal second.

        Returns
        -------
        viscosity : pint.Quantity
            Viscosity (pascal second)
        """
        try:
            viscosity = Q_(super().viscosity(), "pascal second")
        except ValueError:
            # handle error for cubic eos such as PR, SRK etc.
            dummy_state = self.define(
                p=self.p(), T=self.T(), fluid=self.fluid, EOS="REFPROP"
            )
            viscosity = Q_(super(State, dummy_state).viscosity(), "pascal second")
        if units:
            viscosity = viscosity.to(units)
        return viscosity

    def kinematic_viscosity(self, units=None):
        """Kinematic viscosity in m²/s.

        Returns
        -------
        kinematic_viscosity : pint.Quantity
            Kinematic viscosity (m²/s)
        """
        kinematic_viscosity = (self.viscosity() / self.rho()).to("m²/s")
        if units:
            kinematic_viscosity = kinematic_viscosity.to(units)
        return kinematic_viscosity

    def dpdv_s(self, units=None):
        """
        Partial derivative of pressure to spec. volume with const. entropy.
        """
        dpdv_s = Q_(
            -self.rho().magnitude ** 2
            * (self.first_partial_deriv(CP.iP, CP.iDmass, CP.iSmass)),
            "pascal * kg / m**3",
        )
        if units:
            dpdv_s = dpdv_s.to(units)
        return dpdv_s

    def _X(self):
        """ Coeficiente de compressibilidade X de Schultz """
        T = self.T().to("K").magnitude
        V = self.v().to("m³/kg").magnitude

        return Q_(
            -T * V * self.first_partial_deriv(CP.iDmass, CP.iT, CP.iP) - 1,
            "dimensionless",
        )

    def _Y(self):
        """ Coeficiente de compressibilidade X de Schultz """
        P = self.p().to("Pa").magnitude
        V = self.v().to("m³/kg").magnitude

        return Q_(
            -(-P * V * self.first_partial_deriv(CP.iDmass, CP.iP, CP.iT)),
            "dimensionless",
        )

    def kv(self):
        """Isentropic volume exponent (dimensionless).

        Returns
        -------
        kv : pint.Quantity
            Isentropic volume exponent (dimensionless).
        """
        return -(self.v() / self.p()) * self.dpdv_s()

    def dTdp_s(self, units=None):
        """(dT / dp)s

        First partial derivative of temperature related to pressure with
        constant entropy."""
        dTdp_s = Q_(
            super().first_partial_deriv(CP.iT, CP.iP, CP.iSmass), "kelvin / pascal"
        )
        if units:
            dTdp_s = dTdp_s.to(units)

        return dTdp_s

    def kT(self):
        """Isentropic temperature exponent (dimensionless).

        Returns
        -------
        kT : pint.Quantity
            Isentropic temperature exponent (dimensionless).
        """
        return 1 / (1 - (self.p() / self.T()) * self.dTdp_s())

    def conductivity(self, units=None):
        """Thermal conductivity (W/m/K).

        Returns
        -------
        conductivity : pint.Quantity
            Thermal conductivity (W/m/K).
        """
        conductivity = Q_(super().conductivity(), "W/m/degK")
        if units:
            conductivity = conductivity.to(units)
        return conductivity

    def __reduce__(self):
        kwargs = dict(p=self.p(), T=self.T(), fluid=self.fluid)
        return self._rebuild, (self.__class__, kwargs)

    @staticmethod
    def _rebuild(cls, kwargs):
        return cls.define(**kwargs)

    @classmethod
    @check_units
    def define(
        cls,
        p=None,
        T=None,
        h=None,
        s=None,
        rho=None,
        fluid=None,
        EOS=None,
        **kwargs,
    ):
        """Constructor for state.

        Creates a state from fluid composition and two properties.
        Properties can be floats (SI units are considered) or pint quantities.

        Parameters
        ----------
        p : float, pint.Quantity
            Pressure
        T : float, pint.Quantity
            Temperature
        h : float, pint.Quantity
            Enthalpy
        s : float, pint.Quantity
            Entropy
        rho : float, pint.Quantity
            Specific mass

        fluid : dict
            Dictionary with constituent and composition.
            (e.g.: ({'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092})
        EOS : string
            String with HEOS or REFPROP

        Returns
        -------
        state : State object

        Examples
        --------
        >>> import ccp
        >>> Q_ = ccp.Q_
        >>> fluid = {'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092}
        >>> s = ccp.State.define(p=101008, T=273, fluid=fluid)
        >>> s.rho()
        <Quantity(1.28939426, 'kilogram / meter ** 3')>
        >>> # Using pint quantities
        >>> s = ccp.State.define(fluid=fluid, p=Q_(1, 'atm'), T=Q_(0, 'degC'))
        >>> s.h()
        <Quantity(273291.7, 'joule / kilogram')>
        """
        if fluid is None:
            raise TypeError("A fluid is required. Provide as fluid=dict(...)")

        if EOS is None:
            EOS = ccp.config.EOS

        constituents = []
        molar_fractions = []

        for k, v in fluid.items():
            k = get_name(k)
            constituents.append(k)
            molar_fractions.append(v)
            # create an adequate fluid string to cp.AbstractState
        _fluid = "&".join(constituents)

        state = cls(EOS, _fluid)

        normalize_mix(molar_fractions)
        state.set_mole_fractions(molar_fractions)
        state.init_args = dict(p=p, T=T, h=h, s=s, rho=rho)
        state.setup_args = copy(state.init_args)
        state.fluid = state._fluid_dict()
        if isinstance(fluid, str) and len(state.fluid) == 1:
            state.fluid[get_name(fluid)] = 1.0

        if isinstance(fluid, dict):
            if len(state.fluid) < len(fluid):
                raise ValueError(
                    "You might have repeated components in the fluid dictionary."
                )

        state.update(**state.setup_args)

        return state

    @check_units
    def update(
        self,
        p=None,
        T=None,
        rho=None,
        h=None,
        s=None,
        **kwargs,
    ):
        """Update the state.

        This method simplifies the state update. Only keyword arguments are
        required to update.

        Parameters
        ----------
        p : float, pint.Quantity
            Pressure (Pa).
        T : float, pint.Quantity
            Temperature (degk).
        rho : float, pint.Quantity
            Specific mass (kg/m**3).
        h : float, pint.Quantity
            Enthalpy (J/kg).
        s : float, pint.Quantity
            Entropy (J/(kg*degK)).
        """
        if p is not None and T is not None:
            super().update(CP.PT_INPUTS, p.magnitude, T.magnitude)
        elif p is not None and rho is not None:
            super().update(CP.DmassP_INPUTS, rho.magnitude, p.magnitude)
        elif p is not None and h is not None:
            super().update(CP.HmassP_INPUTS, h.magnitude, p.magnitude)
        elif p is not None and s is not None:
            if ccp.config.EOS == "REFPROP":
                super().update(CP.PSmass_INPUTS, p.magnitude, s.magnitude)
            else:
                # ps update not available for some EOS, this is a workaround based on:
                # https://github.com/CoolProp/CoolProp/issues/2000
                def objective(T):
                    super(State, self).update(CP.PT_INPUTS, p.magnitude, T)
                    return self.smass() - s.magnitude

                T0 = self.T().m
                if T0 == float("-inf"):
                    T0 = 300
                newton(objective, x0=T0)
        elif rho is not None and s is not None:
            try:
                super().update(CP.DmassSmass_INPUTS, rho.magnitude, s.magnitude)
            except ValueError:
                # handle convergence error by forcing gas state directly with REFPROP
                # calculate with p and T and update with their values
                fluids = self._fluid.replace("&", "*")
                r = _RP.REFPROPdll(
                    fluids,
                    "DSV",
                    "P,T",
                    _RP.MASS_BASE_SI,
                    0,
                    0,
                    rho.magnitude,
                    s.magnitude,
                    self.get_mole_fractions(),
                )
                super().update(CP.PT_INPUTS, r.Output[0], r.Output[1])
        elif rho is not None and T is not None:
            super().update(CP.DmassT_INPUTS, rho.magnitude, T.magnitude)
        elif h is not None and s is not None:
            super().update(CP.HmassSmass_INPUTS, h.magnitude, s.magnitude)
        elif T is not None and s is not None:
            super().update(CP.SmassT_INPUTS, s.magnitude, T.magnitude)
        else:
            locs = locals()
            for item in ["kwargs", "self", "__class__"]:
                locs.pop(item)
            raise KeyError(
                f"Update key "
                f"{[k for k, v in locs.items() if v is not None]}"
                f" not implemented"
            )

    def plot_envelope(
        self, T_units="degK", p_units="Pa", dew_point_margin=20, fig=None, **kwargs
    ):
        """Plot phase envelope.

        Plots the phase envelope and dew point limit.

        Parameters
        ----------
        T_units : str
            Temperature units.
            Default is 'degK'.
        p_units : str
            Pressure units.
            Default is 'Pa'.
        dew_point_margin : float
            Dew point margin.
            Default is 20 degK (from API). Unit is the same as T_units.
        fig : plotly.graph_objects.Figure, optional
            The figure object with the rotor representation.

        Returns
        -------
        fig : plotly.graph_objects.Figure
            The figure object with the rotor representation.
        """
        if fig is None:
            fig = go.Figure()

        if len(self.fluid) < 2:
            warn(
                "Pure fluids are not fully supported and might break things (e.g. plot_phase_envelope"
                "See https://github.com/CoolProp/CoolProp/issues/1544"
            )

        self.build_phase_envelope("dummy")
        phase_envelope = self.get_phase_envelope_data()
        T = Q_(np.array(phase_envelope.T), "degK").to(T_units).m
        p = Q_(np.array(phase_envelope.p), "Pa").to(p_units).m

        p_lower_bound = Q_(0.1, "atm").to(p_units).m
        T = T[p > p_lower_bound]
        p = p[p > p_lower_bound]

        T_dew = (
            np.add(
                T[: np.argmax(T)], np.multiply(dew_point_margin, np.ones(np.argmax(T)))
            ),
        )
        p_dew = (p[: np.argmax(T)],)

        hovertemplate = (
            f"Temperature ({T_units}): %{{x}}<br>" f"Pressure ({p_units}): %{{y}}"
        )

        fig.add_trace(
            go.Scatter(
                x=T,
                y=p,
                mode="lines",
                hovertemplate=hovertemplate,
                name="Phase Envelope",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=T_dew[0],
                y=p_dew[0],
                mode="lines",
                line=dict(dash="dash"),
                hovertemplate=hovertemplate,
                name=f"Dew Point Margin ({dew_point_margin} {T_units})",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[self.T().to(T_units).m],
                y=[self.p().to(p_units).m],
                hovertemplate=hovertemplate,
                name="State",
            )
        )

        fig.update_layout(
            xaxis=dict(title_text=f"Temperature ({T_units})"),
            yaxis=dict(
                type="log", exponentformat="e", title_text=f"Pressure ({p_units})"
            ),
        )

        return fig

    def plot_point(self, T_units="degK", p_units="Pa", fig=None, **kwargs):
        """Plot point.

        Plot point in the given figure. Function will check for axis units and
        plot the point accordingly.

        Parameters
        ----------
        T_units : str
            Temperature units.
            Default is 'degK'.
        p_units : str
            Pressure units.
            Default is 'Pa'.
        fig : plotly.graph_objects.Figure, optional
            The figure object with the rotor representation.
        kwargs : dict
            Dictionary that will be passed to go.Scatter method.

        Returns
        -------
        fig : plotly.graph_objects.Figure
            The figure object with the rotor representation.
        """
        if fig is None:
            fig = go.Figure()

        p = self.p().to(p_units)
        T = self.T().to(T_units)

        default_values = dict(name="State")

        for k, v in default_values.items():
            kwargs.setdefault(k, v)

        fig.add_trace(
            go.Scatter(
                x=[T.m],
                y=[p.m],
                hovertemplate=f"Temperature ({T_units}): %{{x}}<br>"
                f"Pressure ({p_units}): %{{y}}",
                **kwargs,
            )
        )

        return fig
