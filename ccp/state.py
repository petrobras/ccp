import warnings
from copy import copy

import CoolProp
import CoolProp.CoolProp as CP
import numpy as np
from CoolProp.Plots import PropertyPlot
from CoolProp.Plots.Common import interpolate_values_1d
from bokeh.plotting import figure
from bokeh.models import HoverTool

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
        return Q_(super().gas_constant(), 'joule / (mol kelvin)')

    def molar_mass(self):
        return Q_(super().molar_mass(), 'kg/mol')

    def T(self):
        return Q_(super().T(), 'kelvin')

    def p(self):
        return Q_(super().p(), 'pascal')

    def cp(self):
        return Q_(super().cpmass(), 'joule/(kilogram kelvin)')

    def h(self):
        """Specific Enthalpy (per unit of mass)."""
        return Q_(super().hmass(), 'joule/kilogram')

    def s(self):
        """Specific entropy (per unit of mass)."""
        return Q_(super().smass(), 'joule/(kelvin kilogram)')
    
    def p_crit(self):
        """ Critical Pressure in Pa """
        return Q_(super().p_critical(),'Pa')
    
    def T_crit(self):
        """ Critical Temperature in K """
        return Q_(super().T_critical(),'K')

    def rho(self):
        """Specific mass (kilogram/m**3)."""
        return Q_(super().rhomass(), 'kilogram/m**3')

    def v(self):
        """Specific volume (m**3/kilogram)."""
        return 1 / self.rho()

    def z(self):
        z = (self.p() * self.molar_mass() 
            / (self.rho() * self.gas_constant() * self.T()))
        return z.to('dimensionless')

    def speed_sound(self):
        """ Speed of sound - Eq. 8.1 from P. Nederstigt - Real Gas Thermodynamics"""
        return Q_(np.sqrt(self.first_partial_deriv(CP.iP,CP.iDmass,CP.iSmass)),'m/s')
            

    def viscosity(self):
        return Q_(super().viscosity(), 'pascal second')

    def kinematic_viscosity(self):
        return (self.viscosity() / self.rho()).to('m**2/s')

    def dpdv_s(self):
        """
        Partial derivative of pressure to spec. volume with const. entropy.
        """
        return Q_( - self.rho().magnitude**2 * (self.first_partial_deriv(CP.iP, CP.iDmass, CP.iSmass)),
                'pascal * kg / m**3'
        )
    
    def _X(self):
        """ Coeficiente de compressibilidade X de Schultz """
        T=self.T().to('K').magnitude
        V=self.v().to('m³/kg').magnitude
        
        return Q_(-T*V*self.first_partial_deriv(CP.iDmass,CP.iT,CP.iP)-1,'dimensionless')
    
    def _Y(self):
        """ Coeficiente de compressibilidade X de Schultz """
        P=self.p().to('Pa').magnitude
        V=self.v().to('m³/kg').magnitude
        
        return Q_(-(-P*V*self.first_partial_deriv(CP.iDmass,CP.iP,CP.iT)),'dimensionless')


    def kv(self):
        """Isentropic volume exponent (2.60)."""
        return -(self.v() / self.p()) * self.dpdv_s()

    def dTdp_s(self):
        """(dT / dp)s

        First partial derivative of temperature related to pressure with
        constant entropy."""
        return Q_(super().first_partial_deriv(CP.iT, CP.iP, CP.iSmass),
                  'kelvin / pascal')

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
    def define(cls, p=None, T=None, h=None, s=None, rho=None, fluid=None,
               EOS='REFPROP', **kwargs):
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
            raise TypeError('A fluid is required. Provide as fluid=dict(...)')

        constituents = []
        molar_fractions = []

        # if fluid is a string, consider pure fluid
        try:
            for k, v in fluid.items():
                k = get_name(k)
                constituents.append(k)
                molar_fractions.append(v)
                # create an adequate fluid string to cp.AbstractState
            _fluid = '&'.join(constituents)
        except AttributeError:
            molar_fractions.append(1)
            _fluid = get_name(fluid)

        try:
            state = cls(EOS, _fluid)
        except ValueError:
            raise
            # TODO handle this with better error message, checking hmx.bnc

        normalize_mix(molar_fractions)
        state.set_mole_fractions(molar_fractions)
        state.init_args = dict(p=p, T=T, h=h, s=s, rho=rho)
        state.setup_args = copy(state.init_args)
        state.fluid = state._fluid_dict()

        state.update(**state.setup_args)

        return state

    @check_units
    def update(self, cp_input=None, arg1=None, arg2=None, p=None, T=None,
               rho=None, h=None, s=None, **kwargs):
        """Simple state update.

        This method simplifies the state update. Only keyword arguments are
        required to update.

        Parameters
        ----------
        p : float
            Pressure.
        T : float
            Temperature.
        rho : float
            Specific mass.
        h : float
            Enthalpy.
        s : float
            Entropy
        """
        if cp_input is not None:
            super().update(cp_input, arg1, arg2)
            return

        if p is not None and T is not None:
            super().update(CP.PT_INPUTS,
                           p.magnitude, T.magnitude)
        elif p is not None and rho is not None:
            super().update(CP.DmassP_INPUTS,
                           rho.magnitude, p.magnitude)
        elif p is not None and h is not None:
            super().update(CP.HmassP_INPUTS,
                           h.magnitude, p.magnitude)
        elif p is not None and s is not None:
            super().update(CP.PSmass_INPUTS,
                           p.magnitude, s.magnitude)
        elif rho is not None and s is not None:
            super().update(CP.DmassSmass_INPUTS,
                           rho.magnitude, s.magnitude)
        elif rho is not None and T is not None:
            super().update(CP.DmassT_INPUTS,
                           rho.magnitude, T.magnitude)
        elif h is not None and s is not None:
            super().update(CP.HmassSmass_INPUTS,
                           h.magnitude, s.magnitude)
        elif T is not None and s is not None:
            super().update(CP.SmassT_INPUTS,
                           s.magnitude, T.magnitude)
        else:
            locs = locals()
            for item in ['kwargs', 'self', '__class__']:
                locs.pop(item)
            raise KeyError(f'Update key '
                           f'{[k for k, v in locs.items() if v is not None]}'
                           f' not implemented')

    def plot_point(self, ax, parameters=None, **kwargs):
        """Plot point.
        Plot point in the given axis. Function will check for axis units and
        plot the point accordingly.
        Parameters
        ----------
        ax : matplotlib.axes, optional
            Matplotlib axes, if None creates a new.
        Returns
        -------
        ax : matplotlib.axes
            Matplotlib axes with plot.
        """
        # default plot parameters
        kwargs.setdefault('marker', '2')
        kwargs.setdefault('color', 'k')
        kwargs.setdefault('label', self.__repr__())

        y_value = getattr(self, parameters[0].lower())()
        try:
            x_value = getattr(self, parameters[1].lower())()
        except AttributeError:
            x_value = getattr(self, parameters[1])()

        ax.scatter(x_value, y_value, **kwargs)

    def plot_ph(self, **kwargs):
        """Plot pressure vs enthalpy.

        Returns
        -------
        plot : ccp.ModifiedPropertyPlot
            Object from class inherited from CP.PropertyPlot.

        Examples
        --------
        co2 = ccp.State.define(p=100000, T=300, fluid='co2')
        plot = co2.plot_ph()
        plot.show()
        """
        # copy state to avoid changing it
        _self = copy(self)

        # default values for plot
        kwargs.setdefault('unit_system', 'SI')
        kwargs.setdefault('tp_limits', 'ACHP')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            plot = ModifiedPropertyPlot(_self, 'PH', **kwargs)

            plot.props[CoolProp.iQ]['lw'] = 0.8
            plot.props[CoolProp.iQ]['color'] = 'k'
            plot.props[CoolProp.iQ]['alpha'] = 0.8

            # isothermal
            plot.props[CoolProp.iT]['lw'] = 0.2
            plot.props[CoolProp.iT]['color'] = 'C0'
            plot.props[CoolProp.iT]['alpha'] = 0.2

            plot.props[CoolProp.iSmass]['lw'] = 0.2
            plot.props[CoolProp.iSmass]['color'] = 'C1'
            plot.props[CoolProp.iSmass]['alpha'] = 0.2

            plot.props[CoolProp.iDmass]['lw'] = 0.2
            plot.props[CoolProp.iDmass]['color'] = 'C2'
            plot.props[CoolProp.iDmass]['alpha'] = 0.2

            plot.calc_isolines()

            self.plot_point(plot.axis, parameters='PH')

        return plot

    def plot_pt(self, **kwargs):
        """Plot pressure vs temperature.

        Returns
        -------
        plot : ccp.ModifiedPropertyPlot
            Object from class inherited from CP.PropertyPlot.

        Examples
        --------
        co2 = ccp.State.define(p=100000, T=300, fluid='co2')
        plot = co2.plot_pt()
        plot.show()
        """
        # copy state to avoid changing it
        _self = copy(self)

        # default values for plot
        kwargs.setdefault('unit_system', 'SI')
        kwargs.setdefault('tp_limits', 'ACHP')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            plot = ModifiedPropertyPlot(_self, 'PT', **kwargs)

            plot.props[CoolProp.iQ]['lw'] = 0.8
            plot.props[CoolProp.iQ]['color'] = 'k'
            plot.props[CoolProp.iQ]['alpha'] = 0.8

            plot.props[CoolProp.iSmass]['lw'] = 0.8
            plot.props[CoolProp.iSmass]['color'] = 'C1'
            plot.props[CoolProp.iSmass]['alpha'] = 0.8

            plot.props[CoolProp.iDmass]['lw'] = 0.8
            plot.props[CoolProp.iDmass]['color'] = 'C2'
            plot.props[CoolProp.iDmass]['alpha'] = 0.8

            plot.calc_isolines()

            self.plot_point(plot.axis, parameters='PT')

        return plot

    def plot_envelope(self, fig=None, **kwargs):
        """Plot phase envelope

        Plots the phase envelope and dew point limit.
        """
        if fig is None:
            fig = figure(title='Phase Envelope', y_axis_type='log')

        x_units = kwargs.get('x_units', None)
        y_units = kwargs.get('y_units', None)

        TOOLTIPS = [
            ('T ', f'@x {x_units}'),
            ('p ', f'@y {y_units}'),
        ]
        self.build_phase_envelope("dummy")
        phase_envelope = self.get_phase_envelope_data()
        p = Q_(np.array(phase_envelope.p), 'Pa')
        T = Q_(np.array(phase_envelope.T), 'degK')

        T, p = change_data_units(T, p, x_units, y_units)

        p_lower_bound = Q_(0.1, 'atm')
        T = T[p > p_lower_bound]
        p = p[p > p_lower_bound]

        fig.line(np.add(T.m[:np.argmax(T.m)],
                        np.multiply(12, np.ones(np.argmax(T.m)))),
                 p.m[:np.argmax(T.m)], line_width=4, line_dash='dashed',
                 alpha=0.8, legend='Dewpoint', color='firebrick')

        fig.line(T.m, p.m, line_width=4, alpha=0.8,
                 legend='Phase Envelope')

        fig.add_tools(HoverTool(tooltips=TOOLTIPS, mode='mouse'))


    def __repr__(self):
        args = {k: v for k, v in self.init_args.items() if v is not None}
        args_repr = [f'{k}=Q_("{getattr(self, k)():.0f~P}")' for k, v in args.items()]
        args_repr = ', '.join(args_repr)

        fluid_dict = self.fluid
        sorted_fluid_keys = sorted(fluid_dict, key=fluid_dict.get, reverse=True)
        fluid_repr = [f'"{k}": {fluid_dict[k]:.5f}' for k in sorted_fluid_keys]
        fluid_repr = 'fluid={' + ', '.join(fluid_repr) + '}'

        return 'State.define(' + args_repr + ', ' + fluid_repr + ')'


class ModifiedPropertyPlot(PropertyPlot):
    """Modify CoolProp's property plot."""
    def draw_isolines(self):
        dim_x = self._system[self._x_index]
        dim_y = self._system[self._y_index]

        sat_props = self.props[CoolProp.iQ].copy()
        if 'lw' in sat_props:
            sat_props['lw'] *= 2.0
        else:
            sat_props['lw'] = 1.0
        if 'alpha' in sat_props:
            min([sat_props['alpha'] * 1.0, 1.0])
        else:
            sat_props['alpha'] = 1.0

        for i in self.isolines:
            props = self.props[i]
            dew, bub, x_crit, y_crit = (None,) * 4
            if i == CoolProp.iQ:
                for line in self.isolines[i]:
                    if line.value == 0.0: bub = line
                    elif line.value == 1.0: dew = line
                if dew is not None and bub is not None:
                    xmin, xmax, ymin, ymax = self.get_axis_limits()
                    xmin = dim_x.to_SI(xmin)
                    xmax = dim_x.to_SI(xmax)
                    ymin = dim_y.to_SI(ymin)
                    ymax = dim_y.to_SI(ymax)
                    dx = xmax-xmin
                    dy = ymax-ymin
                    dew_filter = np.logical_and(np.isfinite(dew.x), np.isfinite(dew.y))
                    stp = min([dew_filter.size,10])
                    dew_filter[0:-stp] = False
                    bub_filter = np.logical_and(np.isfinite(bub.x),np.isfinite(bub.y))

                    if self._x_index == CoolProp.iP or self._x_index == CoolProp.iDmass:
                        filter_x = lambda x: np.log10(x)
                    else:
                        filter_x = lambda x: x
                    if self._y_index == CoolProp.iP or self._y_index == CoolProp.iDmass:
                        filter_y = lambda y: np.log10(y)
                    else:
                        filter_y = lambda y: y

                    if ((filter_x(dew.x[dew_filter][-1])-filter_x(bub.x[bub_filter][-1])) < 0.050*filter_x(dx) or
                        (filter_y(dew.y[dew_filter][-1])-filter_y(bub.y[bub_filter][-1])) < 0.010*filter_y(dy)):
                        x = np.linspace(bub.x[bub_filter][-1], dew.x[dew_filter][-1], 11)
                        try:
                            y = interpolate_values_1d(
                              np.append(bub.x[bub_filter],dew.x[dew_filter][::-1]),
                              np.append(bub.y[bub_filter],dew.y[dew_filter][::-1]),
                              x_points=x,
                              kind='cubic')
                            self.axis.plot(dim_x.from_SI(x),dim_y.from_SI(y),**sat_props)
                            warnings.warn("Detected an incomplete phase envelope, fixing it numerically.")
                            x_crit = x[5]
                            y_crit = y[5]
                        except ValueError:
                            continue

            for line in self.isolines[i]:
                if line.i_index == CoolProp.iQ:
                    if line.value == 0.0 or line.value == 1.0:
                        self.axis.plot(dim_x.from_SI(line.x),
                                       dim_y.from_SI(line.y), **sat_props)
                    else:
                        if x_crit is not None and y_crit is not None:
                            self.axis.plot(
                                dim_x.from_SI(np.append(line.x, x_crit)),
                                dim_y.from_SI(np.append(line.y, y_crit)),
                                **props)

                else:
                    self.axis.plot(
                        dim_x.from_SI(line.x), dim_y.from_SI(line.y), **props)
