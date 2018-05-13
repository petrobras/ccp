from copy import copy
from . import Q_
from .config.units import check_units
from .config.fluids import get_name, normalize_mix
import CoolProp.CoolProp as CP


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

    def T(self):
        return Q_(super().T(), 'kelvin')

    def p(self):
        return Q_(super().p(), 'pascal')

    def h(self):
        return Q_(super().hmass(), 'joule/kilogram')

    def s(self):
        return Q_(super().smass(), 'joule/(kelvin kilogram)')

    def rho(self):
        return Q_(super().rhomass(), 'kilogram/m**3')

    def speed_sound(self):
        return Q_(super().speed_sound(), 'm/s')

    def viscosity(self):
        return Q_(super().viscosity(), 'pascal second')

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
            State's pressure
        T : float
            State's temperature
        h : float
            State's enthalpy
        s : float
            State's entropy
        rho : float

        fluid : dict or str
            Dictionary with constituent and composition
            (e.g.: ({'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092})
            A pure fluid can be created with a string.
        EOS : string
            String with HEOS or REFPROP

        Returns
        -------
        state : State object

        Examples:
        ---------
        >>> fluid = {'Oxygen': 0.2096, 'Nitrogen': 0.7812, 'Argon': 0.0092}
        >>> s = State.define(fluid=fluid, p=101008, T=273, EOS='HEOS')
        >>> s.rhomass()
        1.2893965217814896
        >>> # pure fluid
        >>> s = State.define(p=101008, T=273, fluid='CO2')
        >>> s.rho()
        1.9716931060214515
        """
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
            _fluid = fluid

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
    def update(self, p=None, T=None, rho=None, h=None, s=None, **kwargs):
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
        elif h is not None and s is not None:
            super().update(CP.HmassSmass_INPUTS,
                           h.magnitude, s.magnitude)
        else:
            locs = locals()
            for item in ['kwargs', 'self', '__class__']:
                locs.pop(item)
            raise KeyError(f'Update key '
                           f'{[k for k, v in locs.items() if v is not None]}'
                           f' not implemented')

    def __repr__(self):
        args = {k: v for k, v in self.init_args.items() if v is not None}
        args_repr = [f'{k}=Q_("{v:.0f~P}")' for k, v in args.items()]
        args_repr = ', '.join(args_repr)

        fluid_dict = self.fluid
        sorted_fluid_keys = sorted(fluid_dict, key=fluid_dict.get, reverse=True)
        fluid_repr = [f'"{k}": {fluid_dict[k]:.5f}' for k in sorted_fluid_keys]
        fluid_repr = 'fluid={' + ', '.join(fluid_repr) + '}'

        return 'State.define(' + args_repr + ', ' + fluid_repr + ')'


