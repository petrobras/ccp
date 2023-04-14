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
        qm = None,
    ):
        self.state = state
        self.delta_p = delta_p
        self.D = D
        self.d = d.to('m')
        self.tappings = tappings

        if tappings == "corner" or tappings == "D D/2" or tappings == "flange":
            pass
        else:
            raise ValueError('tappings must be "corner", "D D/2" or "flange"')

        if qm is None:
            self.qm = getattr(self,"calc_flow")()
        else:
            self.qm = qm

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

            global qm

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

            qm = (
                C
                / (np.sqrt(1 - beta**4))
                * e
                * (np.pi / 4)
                * d**2
                * np.sqrt(2 * delta_p * rho)
            )

            Reyn_qm = (4 * qm / (mu * np.pi * D)).to("dimensionless").magnitude

            return abs(Reyn_qm - Reyn.magnitude)

        newton(update_Reyn, 1e8, tol=1e-5)

        return qm.to("kg/s")

