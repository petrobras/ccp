"""Flow orifice."""
import numpy as np
from scipy.optimize import newton

from . import Q_


class FlowOrifice:
    def __init__(self, state=None, delta_p=None, qm=None, D=None, tappings="flange"):
        self.state = state
        self.delta_p = delta_p
        self.qm = qm
        self.D = D.to("m")
        self.tappings = tappings

        d = newton(
            calc_d, 0.1, args=(self.state, self.delta_p, self.qm, self.D, self.tappings)
        )
        self.d = Q_(float(d), "m")
        _, self.beta, self.C, self.e, self.reynolds, self.A = calc(
            self.d.magnitude, self.state, self.delta_p, self.qm, self.D, self.tappings
        )

    def update(self):
        d = newton(
            calc_d, 0.1, args=(self.state, self.delta_p, self.qm, self.D, self.tappings)
        )
        self.d = Q_(float(d), "m")

    def __setattr__(self, name, value):
        try:
            if isinstance(getattr(self, name), Q_) and not isinstance(value, Q_):
                super().__setattr__(name, Q_(value, getattr(self, name).units))
            else:
                super().__setattr__(name, value)

        except AttributeError:
            super().__setattr__(name, value)


def calc(x, state=None, delta_p=None, qm=None, D=None, tappings="flange"):
    d = Q_(x, "m")

    # calc beta
    beta = d / D

    p1 = state.p()
    p2 = p1 + delta_p
    rho = state.rho()
    A = np.pi * D ** 2 / 4
    u = qm / (rho * A)
    reyn = (rho * u * D / state.viscosity()).to("dimensionless")

    if tappings == "corner":
        L1 = L2 = 0
    elif tappings == "D D/2":
        L1 = 1
        L2 = 0.47
    elif tappings == "flange":
        L1 = L2 = Q_(0.0254, "m") / D
    else:
        raise ValueError('tappings must be "corner", "D D/2" or "flange"')

    M2 = 2 * L2 / (1 - beta)

    # calc C
    C = (
        0.5961
        + 0.0261 * beta ** 2
        - 0.216 * beta ** 8
        + 0.000521 * (1e6 * beta / reyn) ** 0.7
        + (0.0188 + 0.0063 * (19000 * beta / reyn) ** 0.8)
        * beta ** 3.5
        * (1e6 / reyn) ** 0.3
        + (0.043 + 0.080 * np.e ** (-10 * L1) - 0.123 * np.e ** (-7 * L1))
        * (1 - 0.11 * (19000 * beta / reyn) ** 0.8)
        * (beta ** 4 / (1 - beta ** 4))
        - 0.031 * (M2 - 0.8 * M2 ** 1.1) * beta ** 1.3
    )

    if D < Q_(71.12, "mm"):
        C += 0.011 * (0.75 - beta) * (2.8 - D / 0.0254)

    # calc e
    e = 1 - (0.351 + 0.256 * beta ** 4 + 0.93 * beta ** 8) * (
        1 - (p2 / p1) ** (1 / state.kT())
    )

    # calc qm
    qm_calc = (
        C
        / (np.sqrt(1 - beta ** 4))
        * e
        * (np.pi / 4)
        * d ** 2
        * np.sqrt(2 * delta_p * rho)
    )

    return qm - qm_calc, beta, e, C, reyn, A


def calc_d(x, state=None, delta_p=None, qm=None, D=None, tappings="flange"):
    r = calc(x, state, delta_p, qm, D, tappings)
    return r[0]
