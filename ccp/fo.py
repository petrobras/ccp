"""Flow orifice."""

import numpy as np
from scipy.optimize import newton
from ccp.config.units import check_units
from ccp import Q_


class FlowOrifice:
    @check_units
    def __init__(
        self,
        state=None,
        delta_p=None,
        D=None,
        d=None,
        tappings="flange",
        flow_v=None,
        flow_m=None,
        qm=None,
        state_upstream=True,
    ):
        """Flow orifice.
        Parameters
        ----------
        state : ccp.State
            State of the fluid.
        delta_p : float, pint.Quantity
            Pressure drop across the orifice.
        D : float, pint.Quantity
            Pipe diameter (m).
        d : float, pint.Quantity
            Orifice diameter (m).
        tappings : str, optional
            Tappings of the orifice.
            Default is "flange".
        qm : float, Quantity, optional
            Mass flow rate (kg/s).
        state_upstream : bool, optional
            If the state given is upstream the flow orifice the value is True.
            If it is downstream, the value should be false.
            Default is True.
        Examples
        --------
        >>> import ccp
        >>> Q_ = ccp.Q_
        >>> fluid = {"R134A": 0.018, "R1234ZE": 31.254, "N2": 67.588, "o2": 1.14}
        >>> D = Q_(250, "mm")
        >>> d = Q_(170, "mm")
        >>> p1 = Q_(10, "bar")
        >>> T1 = Q_(40, "degC")
        >>> delta_p = Q_(0.1, "bar")
        >>> state = ccp.State(p=p1, T=T1, fluid=fluid)
        >>> fo = ccp.FlowOrifice(state, delta_p, D, d)
        >>> fo.qm.to("kg/h")
        <Quantity(36408.68715534, 'kilogram / hour')>
        """
        self.state = state
        self.delta_p = delta_p
        self.D = D
        self.d = d
        self.tappings = tappings

        # always consider the state upstream for the rest of calculation
        if not state_upstream:
            self.state.update(p=state.p() + delta_p, T=state.T())

        if tappings == "corner" or tappings == "D D/2" or tappings == "flange":
            pass
        else:
            raise ValueError('tappings must be "corner", "D D/2" or "flange"')
        if flow_m is None and flow_v is None and qm is None:
            self.flow_m = getattr(self, "calc_flow")()
            # keep qm as attribute for backward compatibility
            self.qm = self.flow_m
            self.flow_v = self.flow_m * state.v()
        else:
            self.flow_m = flow_m
            self.qm = qm
            self.flow_v = flow_v

    def calc_flow(self):
        D = self.D
        d = self.d
        delta_p = self.delta_p
        tappings = self.tappings
        state = self.state
        p1 = state.p()
        p2 = p1 - delta_p
        beta = d / D
        mu = state.viscosity()
        rho = state.rho()
        k = state.kv()
        e = 1 - (0.351 + 0.256 * (beta**4) + 0.93 * (beta**8)) * (
            1 - (p2 / p1) ** (1 / k)
        )
        if tappings == "corner":
            L1 = L2 = 0
        elif tappings == "D D/2":
            L1 = 1
            L2 = 0.47
        elif tappings == "flange":
            L1 = L2 = Q_(0.0254, "m") / D
        M2 = 2 * L2 / (1 - beta)

        def update_Reyn(Reyn):
            Reyn = Q_(Reyn, "dimensionless")
            # calc C
            C = (
                0.5961
                + 0.0261 * beta**2
                - 0.216 * beta**8
                + 0.000521 * (1e6 * beta / Reyn) ** 0.7
                + (0.0188 + 0.0063 * (19000 * beta / Reyn) ** 0.8)
                * beta**3.5
                * (1e6 / Reyn) ** 0.3
                + (0.043 + 0.080 * np.e ** (-10 * L1) - 0.123 * np.e ** (-7 * L1))
                * (1 - 0.11 * (19000 * beta / Reyn) ** 0.8)
                * (beta**4 / (1 - beta**4))
                - 0.031 * (M2 - 0.8 * M2**1.1) * beta**1.3
            )
            if D < Q_(71.12, "mm"):
                C += 0.011 * (0.75 - beta) * (2.8 - D / Q_(25.4, "mm"))
            self.flow_m = (
                C
                / (np.sqrt(1 - beta**4))
                * e
                * (np.pi / 4)
                * d**2
                * np.sqrt(2 * delta_p * rho)
            )
            Reyn_qm = (4 * self.flow_m / (mu * np.pi * D)).to("dimensionless").magnitude
            return abs(Reyn_qm - Reyn.magnitude)

        newton(update_Reyn, 1e8, tol=1e-5)
        return self.flow_m.to("kg/s")
