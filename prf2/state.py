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
    # new class to add methods to AbstractState
    # no call to super(). see :
    # http://stackoverflow.com/questions/18260095/
    def __init__(self, EOS, fluid):
        self.EOS = EOS
        self.fluid = fluid

    def T(self):
        return Q_(super().T(), 'kelvin')

    def p(self):
        return Q_(super().p(), 'pascal')

    @classmethod
    @check_units
    def define(cls, p=None, T=None, h=None, s=None, d=None, fluid=None,
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
        d : float

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
        >>> s.rhomass()
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
        state.init_args = dict(p=p, T=T, h=h, s=s, d=d)
        state.setup_args = copy(state.init_args)

        state.update(**state.setup_args)

        return state

    @check_units
    def update(self, *args, **kwargs):
        """Simple state update.

        This method simplifies the state update. Only keyword arguments are
        required to update.

        Parameters
        ----------
        **kwargs : float
            Kwargs with values to update (e.g.: state.update2(p=100200, T=290)
        """
        # TODO add tests to update function.

        # Coolprop case
        if len(kwargs) == 0:
            return super().update(*args)

        inputs = ''.join(k for k, v in kwargs.items() if v is not None)

        order_dict = {'Tp': 'pT',
                      'Qp': 'pQ',
                      'sp': 'ps',
                      'ph': 'hp',
                      'Th': 'hT'}

        if inputs in order_dict:
            inputs = order_dict[inputs]

        cp_update_dict = {'pT': CP.PT_INPUTS,
                          'pQ': CP.PQ_INPUTS,
                          'ps': CP.PSmass_INPUTS,
                          'hp': CP.HmassP_INPUTS,
                          'hT': CP.HmassT_INPUTS}

        try:
            cp_update = cp_update_dict[inputs]
        except KeyError:
            raise KeyError(f'Update key {inputs} not implemented')

        super().update(cp_update,
                       kwargs[inputs[0]].magnitude,
                       kwargs[inputs[1]].magnitude)
