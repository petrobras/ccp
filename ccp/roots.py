"""Scalar root finding for monotone residuals with a physical bracket.

The discharge closures of :class:`ccp.Point` all reduce to one equation in one
variable (a pressure or a temperature) whose residual is monotone between two
physically meaningful states, the suction and the isentropic discharge. The
solver here exploits that: it starts from a guess, brackets the root while it
iterates, never leaves the physical interval and never re-evaluates a state it
already knows. Flash calculations dominate the cost of a closure, so the number
of residual evaluations is what matters.
"""

import math


def solve_monotone(
    f,
    x0,
    lo,
    hi,
    rtol=1e-8,
    increasing=True,
    x1=None,
    max_evals=100,
    name="residual",
    f0=None,
    f1=None,
):
    """Root of a monotone residual ``f`` on ``[lo, hi]``, starting from ``x0``.

    Parameters
    ----------
    f : callable
        Residual ``f(x)``; monotone on ``[lo, hi]``. It may raise ``ValueError``
        or ``ZeroDivisionError`` for a value of ``x`` it cannot evaluate (a
        flash that does not converge, a degenerate state); the step is then
        shortened towards the last good point.
    x0 : float
        Initial guess.
    lo, hi : float
        Physical interval that contains the root. The ends are only evaluated
        when the iteration is clamped to them.
    rtol : float, optional
        Relative tolerance on ``x``: the iteration stops when the bracket
        width or the last step is below ``rtol * |x|``. Default 1e-8.
    increasing : bool, optional
        True when ``f`` increases with ``x`` (default), False when it decreases.
    x1 : float, optional
        Second guess; when given, the first step is the secant through
        ``x0`` and ``x1`` instead of a geometric step from ``x0``.
    max_evals : int, optional
        Maximum number of residual evaluations. Default 100.
    name : str, optional
        Label used in error messages.
    f0, f1 : float, optional
        Residuals already known at ``x0`` and ``x1``; they are used instead
        of evaluating ``f`` there.

    Returns
    -------
    x : float
        The root.

    Raises
    ------
    ValueError
        When the residual has the same sign at ``lo`` and ``hi`` (no root in
        the interval), when ``f`` cannot be evaluated around the iterate, or
        when ``max_evals`` is exceeded.
    """
    if not lo < hi:
        raise ValueError(f"{name}: empty bracket [{lo}, {hi}]")
    sign = 1.0 if increasing else -1.0

    evals = 0

    known = {}
    if f0 is not None:
        known[min(max(x0, lo), hi)] = f0
    if f1 is not None and x1 is not None:
        known[min(max(x1, lo), hi)] = f1

    def g(x):
        # residual with the sign normalised so that g increases with x
        nonlocal evals
        if x in known:
            return sign * known.pop(x)
        evals += 1
        return sign * f(x)

    # bracket ends found so far: a has g < 0, b has g > 0
    a = ga = b = gb = None
    a_last = False  # which end the last evaluation replaced
    same_side = 0  # consecutive replacements of the same bracket end
    # the last two evaluations, for the secant
    xp = gp = None

    x = min(max(x0, lo), hi)
    x_next = None if x1 is None else min(max(x1, lo), hi)
    step = 0.02  # geometric step from the guess, doubled while unbracketed
    tiny = 1e-300

    while True:
        if evals >= max_evals:
            raise ValueError(
                f"{name}: no convergence after {evals} evaluations "
                f"(bracket [{a}, {b}], residuals [{ga}, {gb}])"
            )
        try:
            gx = g(x)
        except (ValueError, ZeroDivisionError) as exc:
            # shorten the step towards the last good point; at the very first
            # evaluation, walk towards the middle of the physical interval
            target = 0.5 * (lo + hi) if xp is None else xp
            x_bad = x
            x = 0.5 * (x + target)
            x_next = None
            if abs(x - x_bad) <= rtol * max(abs(x), tiny):
                raise ValueError(
                    f"{name}: cannot be evaluated at {x_bad}: {exc}"
                ) from exc
            continue

        if gx == 0.0:
            return x
        if math.isnan(gx):
            # like a failed evaluation: shorten the step
            target = 0.5 * (lo + hi) if xp is None else xp
            x_bad = x
            x = 0.5 * (x + target)
            x_next = None
            if abs(x - x_bad) <= rtol * max(abs(x), tiny):
                raise ValueError(f"{name}: not a number at x = {x_bad}")
            continue

        # update the bracket
        bracketed_before = a is not None and b is not None
        if gx < 0.0:
            same_side = same_side + 1 if bracketed_before and a_last else 0
            a, ga, a_last = x, gx, True
        else:
            same_side = same_side + 1 if bracketed_before and not a_last else 0
            b, gb, a_last = x, gx, False

        if a is not None and b is not None:
            # bracketed: converged when the bracket is tight enough
            width = b - a
            tol = rtol * max(abs(a), abs(b), tiny)
            if width <= tol:
                return a - ga * width / (gb - ga)
            candidate = None
            if same_side < 3:
                # secant through the last two points when it lands strictly
                # inside the bracket
                if xp is not None and gp != gx:
                    candidate = x - gx * (x - xp) / (gx - gp)
                    if a < candidate < b:
                        if abs(candidate - x) <= tol:
                            # the secant step is below the tolerance and the
                            # root is bracketed: the remaining error is
                            # smaller than the step
                            return candidate
                    else:
                        candidate = None
                if candidate is None:
                    # regula falsi, Illinois-weighted when one end stalls
                    wa, wb = ga, gb
                    if same_side >= 1:
                        if a_last:
                            wb = 0.5 * gb
                        else:
                            wa = 0.5 * ga
                    candidate = a - wa * (b - a) / (wb - wa)
                # keep the candidate off the ends so the bracket shrinks
                if candidate - a < 0.5 * tol:
                    candidate = a + 0.5 * tol
                if b - candidate < 0.5 * tol:
                    candidate = b - 0.5 * tol
            if candidate is None or not (a < candidate < b):
                candidate = 0.5 * (a + b)
                same_side = 0
            xp, gp = x, gx
            x = candidate
            continue

        # not bracketed yet: move towards the root
        direction = 1.0 if gx < 0.0 else -1.0
        if (direction > 0 and x >= hi) or (direction < 0 and x <= lo):
            end = "upper" if direction > 0 else "lower"
            raise ValueError(
                f"{name}: no root in [{lo}, {hi}] "
                f"(residual {sign * gx} at the {end} end {x})"
            )
        candidate = None
        if x_next is not None:
            candidate = x_next
            x_next = None
        elif xp is not None and gp != gx:
            candidate = x - gx * (x - xp) / (gx - gp)
            if (candidate - x) * direction <= 0.0:
                # the secant points away from the root
                candidate = None
            elif abs(candidate - x) <= rtol * max(abs(x), tiny):
                # one-sided superlinear convergence: the remaining error is
                # smaller than this step
                return candidate
        if candidate is None:
            candidate = x * (1.0 + direction * step) if x != 0.0 else direction * step
            step *= 2.0
        else:
            # limit the move so a poor secant cannot run away
            max_move = max(0.25 * abs(x), 0.1 * (hi - lo))
            if abs(candidate - x) > max_move:
                candidate = x + direction * max_move
        candidate = min(max(candidate, lo), hi)
        xp, gp = x, gx
        x = candidate
