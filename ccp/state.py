import warnings
from copy import copy

import CoolProp
import CoolProp.CoolProp as CP
import numpy as np
from CoolProp.Plots import PropertyPlot
from CoolProp.Plots.Common import interpolate_values_1d
from plotly import graph_objects as go
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource

from . import Q_
from .config.fluids import get_name, normalize_mix
from .config.units import check_units, change_data_units


class State(CP.AbstractState):
    """State class.

    This class is inherited from CP.AbstractState.
    Some extra functionality has been added.
    To create a State see constructor .define().
    """

    def __init__(self, EOS, _fluid):
        # no call to super(). see :
        # http://stackoverflow.com/questions/18260095/
        self.EOS = EOS
        self._fluid = _fluid

    def _fluid_dict(self):
        # preserve the dictionary from define method
        fluid_dict = {}
        for k, v in zip(self.fluid_names(), self.get_mole_fractions()):
            fluid_dict[k] = v
            self.fluid = fluid_dict
        return fluid_dict

    def gas_constant(self):
        return Q_(super().gas_constant(), "joule / (mol kelvin)")

    def molar_mass(self):
        return Q_(super().molar_mass(), "kg/mol")

    def T(self):
        return Q_(super().T(), "kelvin")

    def p(self):
        return Q_(super().p(), "pascal")

    def cp(self):
        return Q_(super().cpmass(), "joule/(kilogram kelvin)")

    def cv(self):
        return Q_(super().cvmass(), "joule/(kilogram kelvin)")

    def h(self):
        """Specific Enthalpy (per unit of mass)."""
        return Q_(super().hmass(), "joule/kilogram")

    def s(self):
        """Specific entropy (per unit of mass)."""
        return Q_(super().smass(), "joule/(kelvin kilogram)")

    def p_crit(self):
        """ Critical Pressure in Pa """
        return Q_(super().p_critical(), "Pa")

    def T_crit(self):
        """ Critical Temperature in K """
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
        return Q_(super().viscosity(), "pascal second")

    def kinematic_viscosity(self):
        return (self.viscosity() / self.rho()).to("m**2/s")

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
        """Isentropic volume exponent (2.60)."""
        return -(self.v() / self.p()) * self.dpdv_s()

    def dTdp_s(self):
        """(dT / dp)s

        First partial derivative of temperature related to pressure with
        constant entropy."""
        return Q_(
            super().first_partial_deriv(CP.iT, CP.iP, CP.iSmass), "kelvin / pascal"
        )

    def kT(self):
        """Isentropic temperature exponent (2.61)."""
        return 1 / (1 - (self.p() / self.T()) * self.dTdp_s())

    def __reduce__(self):
        # fluid_ = self.fluid
        # kwargs = {k: v for k, v in self.init_args.items() if v is not None}
        kwargs = dict(p=self.p(), T=self.T(), fluid=self.fluid)
        # kwargs['fluid'] = fluid_
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

        fluid : dict or str
            Dictionary with constituent and composition
            (e.g.: ({'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092})
            A pure fluid can be created with a string.
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
        >>> # pure fluid
        >>> s = State.define(p=101008, T=273, fluid='CO2')
        >>> s.rho()
        1.9716931060214515
        """
        if fluid is None:
            raise TypeError("A fluid is required. Provide as fluid=dict(...)")

        constituents = []
        molar_fractions = []

        # if fluid is a string, consider pure fluid
        try:
            for k, v in fluid.items():
                k = get_name(k)
                constituents.append(k)
                molar_fractions.append(v)
                # create an adequate fluid string to cp.AbstractState
            _fluid = "&".join(constituents)
        except AttributeError:
            # workaround https://github.com/CoolProp/CoolProp/issues/1544
            # so we can build phase envelopes for pure substances
            molar_fractions = [1 - 1e-15, 1e-15]
            # First try to use the same fluid, if it does not work, use a mixture with a different fluid.
            _fluid = f"{get_name(fluid)}&{get_name(fluid)}"

        try:
            state = cls(EOS, _fluid)
        except ValueError:
            mix_options = [get_name(f) for f in ("n2", "o2")]
            if get_name(fluid) != mix_options[0]:
                _fluid = f"{get_name(fluid)}&{mix_options[0]}"
            else:
                _fluid = f"{get_name(fluid)}&{mix_options[1]}"
            state = cls(EOS, _fluid)
            # TODO handle this with better error message, checking hmx.bnc

        normalize_mix(molar_fractions)
        state.set_mole_fractions(molar_fractions)
        state.init_args = dict(p=p, T=T, h=h, s=s, rho=rho)
        state.setup_args = copy(state.init_args)
        state.fluid = state._fluid_dict()

        state.update(**state.setup_args)

        return state

    @check_units
    def update(
        self, p=None, T=None, rho=None, h=None, s=None, **kwargs,
    ):
        """Simple state update.

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
