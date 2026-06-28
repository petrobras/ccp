"""Gaussian-process surrogate converter for Impeller performance maps.

Backs ``ccp.Impeller.convert_from(..., method="gp_surrogate")``. Fits
``psi, eff = f(phi, M_tip)`` over one or more measured maps of a machine and
re-dimensionalizes the prediction at a new suction state. No persistence: the model is
refit on every call (fitting is ~1-2 s, negligible next to building the converted map).

Instead of thermodynamically re-scaling a single source map onto a new suction (which
diverges for dense / supercritical CO2-rich suctions, where ``convert_from``'s
enthalpy-entropy flash fails to converge), this fits a per-machine surrogate of the
non-dimensional map over *all* measured cases and evaluates it at the target suction.

The identified invariants are the flow coefficient ``phi`` and the tip Mach number
``M_tip``; Reynolds / volume-ratio are collinear with ``M_tip`` and add nothing, and
compressibility ``Z`` adds nothing measurable (leave-one-case-out tested). So the
surrogate inputs are exactly ``(phi, M_tip)``.

Re-dimensionalization uses ccp's own coefficient definitions (``ccp/point.py``), with
``u = speed * D / 2``::

    M_tip  = u / suc.speed_sound()
    flow_v = phi * pi * D**2 * u / 4      (from phi = flow_v * 4 / (pi * D**2 * u))
    head   = psi * u**2 / 2               (from psi = head / (u**2 / 2))
    eff    = eff                          (clipped to (1e-3, 0.999))
"""

from __future__ import annotations

import numpy as np

import ccp

Q_ = ccp.Q_


def _point_features(impellers):
    """Collect ``(phi, M_tip, psi, eff)`` from every point of every impeller."""
    phi, mach, psi, eff = [], [], [], []
    for imp in impellers:
        for curve in imp.curves:
            for p in curve.points:
                phi.append(p.phi.m)
                mach.append(p.mach.m)
                psi.append(p.psi.m)
                eff.append(p.eff.m)
    return tuple(np.asarray(a) for a in (phi, mach, psi, eff))


def _curve_phi_envelopes(impellers):
    """Per-speed-line ``(M_tip, phi_lo, phi_hi)``, sorted by Mach.

    Every point on a measured speed line shares the same tip Mach (``u`` and the suction
    speed of sound are both constant along it), so each curve contributes one
    ``(Mach, min phi, max phi)`` sample of the map's flow envelope.
    """
    mach, phi_lo, phi_hi = [], [], []
    for imp in impellers:
        for curve in imp.curves:
            phis = [p.phi.m for p in curve.points]
            mach.append(curve.points[0].mach.m)
            phi_lo.append(min(phis))
            phi_hi.append(max(phis))
    order = np.argsort(mach)
    return (
        np.asarray(mach)[order],
        np.asarray(phi_lo)[order],
        np.asarray(phi_hi)[order],
    )


def _interp_extrap(x, xp, fp, min_gap=0.03):
    """Linear interpolation of ``fp(xp)`` at ``x`` with linear extrapolation outside.

    Inside ``[xp[0], xp[-1]]`` this is ``np.interp``. Outside, it continues the slope of
    the nearest end *segment* -- but the segment is measured against the nearest training
    point at least ``min_gap`` away in ``x``, so two speed lines that happen to sit at
    almost the same Mach (e.g. one per training map) can't blow the slope up.
    """
    xp = np.asarray(xp, dtype=float)
    fp = np.asarray(fp, dtype=float)
    if len(xp) == 1:
        return float(fp[0])
    if x <= xp[0]:
        j = int(np.searchsorted(xp, xp[0] + min_gap))
        j = min(max(j, 1), len(xp) - 1)
        slope = (fp[j] - fp[0]) / (xp[j] - xp[0]) if xp[j] > xp[0] else 0.0
        return float(fp[0] + slope * (x - xp[0]))
    if x >= xp[-1]:
        i = int(np.searchsorted(xp, xp[-1] - min_gap)) - 1
        i = min(max(i, 0), len(xp) - 2)
        slope = (fp[-1] - fp[i]) / (xp[-1] - xp[i]) if xp[-1] > xp[i] else 0.0
        return float(fp[-1] + slope * (x - xp[-1]))
    return float(np.interp(x, xp, fp))


class _GPSurrogate:
    """Per-machine GP surrogate of ``psi(phi, M_tip)`` and ``eff(phi, M_tip)``."""

    def __init__(self, gp_psi, gp_eff, x_mean, x_std, env_mach, env_lo, env_hi, b, D):
        self.gp_psi = gp_psi
        self.gp_eff = gp_eff
        self.x_mean = x_mean
        self.x_std = x_std
        # per-speed-line flow (phi) envelope vs tip Mach, for Mach-local phi ranges
        self.env_mach = env_mach
        self.env_lo = env_lo
        self.env_hi = env_hi
        self.b = b
        self.D = D

    @classmethod
    def fit(cls, impellers):
        """Fit the surrogate on a list of (measured) ``ccp.Impeller`` objects."""
        try:
            from sklearn.gaussian_process import GaussianProcessRegressor
            from sklearn.gaussian_process.kernels import (
                RBF,
                ConstantKernel,
                WhiteKernel,
            )
        except ImportError as e:
            raise ImportError(
                "method='gp_surrogate' requires scikit-learn. "
                "Install it with: pip install scikit-learn"
            ) from e

        phi, mach, psi, eff = _point_features(impellers)
        X = np.column_stack([phi, mach])
        x_mean = X.mean(0)
        x_std = X.std(0)
        x_std[x_std == 0] = 1.0
        Xs = (X - x_mean) / x_std

        def _make():
            # Bound the RBF length-scales (features are standardized, so std=1). Without
            # an upper bound the optimizer intermittently drives the phi length-scale
            # huge -> the target loses its phi dependence and collapses to a flat (mean)
            # prediction (seen as a flat efficiency line). The good optima sit at ~0.8-5,
            # so (0.1, 10) keeps them and forbids the degenerate flat fit. random_state
            # makes the multi-restart optimization reproducible.
            kernel = ConstantKernel(1.0, (1e-2, 1e2)) * RBF(
                [1.0, 1.0], length_scale_bounds=(0.1, 10.0)
            ) + WhiteKernel(1e-3, (1e-6, 1e-1))
            return GaussianProcessRegressor(
                kernel=kernel,
                normalize_y=True,
                n_restarts_optimizer=5,
                alpha=1e-6,
                random_state=0,
            )

        gp_psi = _make().fit(Xs, psi)
        gp_eff = _make().fit(Xs, eff)

        env_mach, env_lo, env_hi = _curve_phi_envelopes(impellers)
        p0 = impellers[0].points[0]
        return cls(gp_psi, gp_eff, x_mean, x_std, env_mach, env_lo, env_hi, p0.b, p0.D)

    def _predict(self, phi, mach):
        X = np.column_stack([np.atleast_1d(phi), np.atleast_1d(mach)])
        Xs = (X - self.x_mean) / self.x_std
        return self.gp_psi.predict(Xs), self.gp_eff.predict(Xs)

    def _phi_range_for_mach(self, mach):
        """Flow (phi) range of the converted speed line at tip Mach ``mach``.

        Mach is the GP's second input and the ``(phi, M)`` data is correlated (higher-Mach
        lines surge/choke at higher phi), so the valid phi band shifts with Mach. Each
        training speed line gives one ``(Mach, phi_lo, phi_hi)`` sample; we interpolate
        phi_lo and phi_hi across those vs Mach (and *extrapolate* the trend beyond the
        sampled Mach range). This matters because converting to a new suction shifts the
        whole operating Mach range -- e.g. a high-speed-of-sound target pushes the low
        speed lines *below* the training Mach range. The earlier nearest-points approach
        then grabbed phi from higher-Mach lines and produced a too-wide, too-high flow
        band (the converted low-speed curve overshot the measured flow envelope on both
        ends). Following the per-line trend instead reproduces the measured flow range.
        A safety band keeps far extrapolation from running away.
        """
        lo = _interp_extrap(mach, self.env_mach, self.env_lo)
        hi = _interp_extrap(mach, self.env_mach, self.env_hi)
        g_lo = float(self.env_lo.min())
        g_hi = float(self.env_hi.max())
        lo = min(max(lo, 0.5 * g_lo), 1.5 * g_hi)
        hi = min(max(hi, 0.5 * g_lo), 1.5 * g_hi)
        if hi <= lo:
            hi = lo * 1.05
        return lo, hi

    def convert(self, suc, speeds, n_points=10):
        """Build converted ``ccp.Point`` objects at ``suc`` for the given speed lines."""
        D = self.D
        a_suc = suc.speed_sound()

        points = []
        for speed in speeds:
            u = (speed * D / 2).to("m/s")
            mach = (u / a_suc).to("dimensionless").m
            # Mach-local phi envelope: keep each converted line within the phi support the
            # GP actually has at this tip Mach, so it interpolates instead of extrapolating.
            phi_lo, phi_hi = self._phi_range_for_mach(mach)
            phi_grid = np.linspace(phi_lo, phi_hi, n_points)
            psi_hat, eff_hat = self._predict(phi_grid, np.full(n_points, mach))
            for phi_v, psi_v, eff_v in zip(phi_grid, psi_hat, eff_hat):
                flow_v = phi_v * np.pi * D**2 * u / 4
                head = psi_v * u**2 / 2
                points.append(
                    ccp.Point(
                        suc=suc,
                        flow_v=flow_v.to("m**3/s"),
                        speed=speed,
                        head=head.to("J/kg"),
                        eff=Q_(float(np.clip(eff_v, 1e-3, 0.999)), "dimensionless"),
                        b=self.b,
                        D=D,
                    )
                )
        return points


def _output_speeds(impellers, speed):
    """Speed lines for the converted map (see plan §7).

    The surrogate has no single "source map" to copy speeds from. If ``speed`` is a
    number / ``Q_``, emit a single curve at that speed. Otherwise (``None`` or
    ``"same"``) use the speed lines of the most complete training map -- the impeller
    with the most curves, ties broken by list order. Taking one map's speeds (rather than
    a union across maps) avoids spurious near-duplicate lines.
    """
    if speed is not None and speed != "same":
        return [speed if hasattr(speed, "to") else Q_(speed, "RPM")]
    best = max(impellers, key=lambda im: len(im.curves))
    return [c.speed for c in best.curves]


def convert_from_gp_surrogate(
    impeller_cls, original_impeller, suc, speed=None, n_points=10
):
    """Entry point used by ``Impeller.convert_from(method='gp_surrogate')``.

    Fits a GP surrogate on ``original_impeller`` (a single ``Impeller`` or a list) and
    re-dimensionalizes it at ``suc``.
    """
    impellers = (
        original_impeller
        if isinstance(original_impeller, list)
        else [original_impeller]
    )
    if suc is None:
        raise ValueError("suc is required for method='gp_surrogate'")

    # The non-dimensional coefficients assume a single geometry; require matching b, D.
    p0 = impellers[0].points[0]
    for imp in impellers[1:]:
        p = imp.points[0]
        if not np.isclose(p.b.to("m").m, p0.b.to("m").m) or not np.isclose(
            p.D.to("m").m, p0.D.to("m").m
        ):
            raise ValueError(
                "method='gp_surrogate' requires all impellers to share the same "
                "geometry (b, D); got differing values across the supplied maps."
            )

    model = _GPSurrogate.fit(impellers)
    out_speeds = _output_speeds(impellers, speed)
    points = model.convert(suc, out_speeds, n_points=n_points)
    return impeller_cls(points)
