from copy import copy
from warnings import warn

import CoolProp.CoolProp as CP
import numpy as np
from plotly import graph_objects as go

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
    Properties should be in SI units, **kwargs can be passed
    to change units.

    Parameters
    ----------
    p : float
        Pressure
    T : float
        Temperature
    h : float
        Enthalpy
    s : float
        Entropy
    rho : float
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
    >>> fluid = {'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092}
    >>> s = State.define(fluid=fluid, p=101008, T=273, EOS='HEOS')
    >>> s.rhomass()
    1.2893965217814896
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

    def gas_constant(self):
        """Gas constant in joule / (mol kelvin).

        Returns
        -------
        gas_constant : pint.Quantity
            Gas constant (joule / (mol kelvin).
        """
        return Q_(super().gas_constant(), "joule / (mol kelvin)")

    def molar_mass(self):
        """Molar mass in kg/mol.

        Returns
        -------
        molar_mass : pint.Quantity
            Molar mass (kg/mol).
        """
        return Q_(super().molar_mass(), "kg/mol")

    def T(self):
        """Temperature in Kelvin.

        Returns
        -------
        T : pint.Quantity
            Temperature (Kelvin).
        """
        return Q_(super().T(), "kelvin")

    def p(self):
        """Pressure in Pascal.

        Returns
        -------
        p : pint.Quantity
            Pressure (pascal).
        """
        return Q_(super().p(), "pascal")

    def cp(self):
        """Specific heat at constant pressure joule/(kilogram kelvin).

        Returns
        -------
        cp : pint.Quantity
            Specific heat at constant pressure joule/(kilogram kelvin).
        """
        return Q_(super().cpmass(), "joule/(kilogram kelvin)")

    def cv(self):
        """Specific heat at constant volume joule/(kilogram kelvin).

        Returns
        -------
        cv : pint.Quantity
            Specific heat at constant volume joule/(kilogram kelvin).
        """
        return Q_(super().cvmass(), "joule/(kilogram kelvin)")

    def h(self):
        """Specific Enthalpy (joule/kilogram).

        Returns
        -------
        h : pint.Quantity
            Enthalpy (joule/kilogram).
        """
        return Q_(super().hmass(), "joule/kilogram")

    def s(self):
        """Specific entropy (per unit of mass)."""
        return Q_(super().smass(), "joule/(kelvin kilogram)")

    def p_critical(self):
        """Critical Pressure in Pa"""
        return Q_(super().p_critical(), "Pa")

    def T_critical(self):
        """Critical Temperature in K"""
        return Q_(super().T_critical(), "K")

    def rho(self):
        """Specific mass (kilogram/m**3)."""
        return Q_(super().rhomass(), "kilogram/m**3")

    def v(self):
        """Specific volume (m**3/kilogram)."""
        return 1 / self.rho()

    def z(self):
        z = self.p() * self.molar_mass() / (self.rho() * self.gas_constant() * self.T())
        return z.to("dimensionless")

    def speed_sound(self):
        """ Speed of sound - Eq. 8.1 from P. Nederstigt - Real Gas Thermodynamics"""
        return Q_(np.sqrt(self.first_partial_deriv(CP.iP, CP.iDmass, CP.iSmass)), "m/s")

    def viscosity(self):
        """Viscosity in pascal second.

        Returns
        -------
        viscosity : pint.Quantity
            Viscosity (pascal second)
        """
        return Q_(super().viscosity(), "pascal second")

    def kinematic_viscosity(self):
        """Kinematic viscosity in m²/s.

        Returns
        -------
        kinematic_viscosity : pint.Quantity
            Kinematic viscosity (m²/s)
        """
        return (self.viscosity() / self.rho()).to("m²/s")

    def dpdv_s(self):
        """
        Partial derivative of pressure to spec. volume with const. entropy.
        """
        return Q_(
            -self.rho().magnitude ** 2
            * (self.first_partial_deriv(CP.iP, CP.iDmass, CP.iSmass)),
            "pascal * kg / m**3",
        )

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

    def dTdp_s(self):
        """(dT / dp)s

        First partial derivative of temperature related to pressure with
        constant entropy."""
        return Q_(
            super().first_partial_deriv(CP.iT, CP.iP, CP.iSmass), "kelvin / pascal"
        )

    def kT(self):
        """Isentropic temperature exponent (dimensionless).

        Returns
        -------
        kT : pint.Quantity
            Isentropic temperature exponent (dimensionless).
        """
        return 1 / (1 - (self.p() / self.T()) * self.dTdp_s())

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
        EOS="REFPROP",
        **kwargs,
    ):
        """Constructor for state.

        Creates a state from fluid composition and two properties.
        Properties should be in SI units, **kwargs can be passed
        to change units.

        Parameters
        ----------
        p : float
            Pressure
        T : float
            Temperature
        h : float
            Enthalpy
        s : float
            Entropy
        rho : float
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
        >>> fluid = {'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092}
        >>> s = State.define(fluid=fluid, p=101008, T=273, EOS='HEOS')
        >>> s.rhomass()
        1.2893965217814896
        """
        if fluid is None:
            raise TypeError("A fluid is required. Provide as fluid=dict(...)")

        constituents = []
        molar_fractions = []

        if len(fluid) < 2:
            warn(
                "Pure fluids are not fully supported and might break things (e.g. plot_phase_envelope"
                "See https://github.com/CoolProp/CoolProp/issues/1544"
            )

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
        self, p=None, T=None, rho=None, h=None, s=None, **kwargs,
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
            super().update(CP.PSmass_INPUTS, p.magnitude, s.magnitude)
        elif rho is not None and s is not None:
            super().update(CP.DmassSmass_INPUTS, rho.magnitude, s.magnitude)
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
