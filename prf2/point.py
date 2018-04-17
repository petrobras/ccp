from copy import copy


class Point:
    """Point.
    A point in the compressor map that can be defined in different ways.

    Parameters
    ----------
    speed : float
        Speed in 1/s.
    flow_v or flow_m : float
        Volumetric or mass flow.
    suc, disch : prf.State, prf.State
        Suction and discharge states for the point.
    suc, head, eff : prf.State, float, float
        Suction state, polytropic head and polytropic efficiency.
    suc, head, power : prf.State, float, float
        Suction state, polytropic head and gas power.
    suc, eff, vol_ratio : prf.State, float, float
        Suction state, polytropic efficiecy and volume ratio.

    Returns
    -------
    Point : prf.Point
        A point in the compressor map.
    """
    def __init__(self, *, speed, **kwargs):
        flow_v = kwargs.get('flow_v', None)
        flow_m = kwargs.get('flow_m', None)
        if flow_v is None and flow_m is None:
            raise TypeError("__init__() missing 1 required keyword-only"
                            " argument: 'flow_v' or 'flow_m'.")

        # dummy state used to avoid copying states
        self._dummy_state = copy(self.suc)
