"""
Optimize hydrocarbon composition to achieve target density, velocity of sound,
specific heat at constant pressure, specific heat at constant volume, and compressibility factor.

This script creates a ccp.State with a hydrocarbon mixture and uses scipy optimization
to adjust the composition to achieve target thermodynamic properties.
"""

import numpy as np
from scipy.optimize import minimize
from ccp import Q_, State


def objective_function(
    composition_fractions,
    components,
    T,
    p,
    target_rho,
    target_w,
    target_cp=None,
    target_cv=None,
    target_z=None,
):
    """
    Objective function to minimize - difference from target properties.

    Parameters
    ----------
    composition_fractions : array-like
        Current composition fractions (to be optimized)
    components : list
        List of component names
    T : pint.Quantity
        Temperature
    p : pint.Quantity
        Pressure
    target_rho : pint.Quantity
        Target density
    target_w : pint.Quantity
        Target velocity of sound
    target_cp : pint.Quantity, optional
        Target specific heat at constant pressure
    target_cv : pint.Quantity, optional
        Target specific heat at constant volume
    target_z : float, optional
        Target compressibility factor

    Returns
    -------
    float
        Sum of squared relative errors
    """
    try:
        # Create state with current composition
        fluid = {comp: frac for comp, frac in zip(components, composition_fractions)}
        state = State(fluid=fluid, T=T, p=p)

        # Calculate current properties
        current_rho = state.rho()
        current_w = state.speed_sound()

        # Calculate relative errors for required properties
        rho_error = ((current_rho - target_rho) / target_rho).m_as("dimensionless")
        w_error = ((current_w - target_w) / target_w).m_as("dimensionless")

        # Start with base errors
        total_error = rho_error**2 + w_error**2

        # Add optional target errors if specified
        if target_cp is not None:
            current_cp = state.cp()
            cp_error = ((current_cp - target_cp) / target_cp).m_as("dimensionless")
            total_error += cp_error**2

        if target_cv is not None:
            current_cv = state.cv()
            cv_error = ((current_cv - target_cv) / target_cv).m_as("dimensionless")
            total_error += cv_error**2

        if target_z is not None:
            current_z = state.z()
            z_error = (current_z - target_z) / target_z
            total_error += z_error**2

        return total_error

    except Exception as e:
        # Return large penalty if state calculation fails
        print(f"State calculation failed: {e}")
        return 1e10


def optimize_composition(
    components,
    initial_composition,
    T,
    p,
    target_rho,
    target_w,
    target_cp=None,
    target_cv=None,
    target_z=None,
):
    """
    Optimize hydrocarbon composition to achieve target properties.

    Parameters
    ----------
    components : list
        List of component names (e.g., ['methane', 'ethane', 'propane'])
    initial_composition : dict
        Initial composition as {component: fraction}
    T : pint.Quantity
        Temperature
    p : pint.Quantity
        Pressure
    target_rho : pint.Quantity
        Target density
    target_w : pint.Quantity
        Target velocity of sound
    target_cp : pint.Quantity, optional
        Target specific heat at constant pressure
    target_cv : pint.Quantity, optional
        Target specific heat at constant volume
    target_z : float, optional
        Target compressibility factor

    Returns
    -------
    dict
        Optimized composition
    State
        Final state with optimized composition
    """
    # Convert initial composition to array
    initial_fractions = np.array(
        [initial_composition.get(comp, 0) for comp in components]
    )
    initial_fractions = initial_fractions / initial_fractions.sum()

    # Constraints: fractions must sum to 1 and be non-negative
    constraints = [
        {"type": "eq", "fun": lambda x: x.sum() - 1}  # Sum to 1
    ]

    # Bounds: each fraction between 0 and 1
    bounds = [(0, 1) for _ in components]

    # Optimize
    result = optimize.minimize(
        objective_function,
        initial_fractions,
        args=(components, T, p, target_rho, target_w, target_cp, target_cv, target_z),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 1000},
    )

    if not result.success:
        print(f"Warning: Optimization did not fully converge: {result.message}")

    # Get optimized composition
    optimized_fractions = result.x
    optimized_fractions = (
        optimized_fractions / optimized_fractions.sum()
    )  # Ensure normalized

    # Create final composition dictionary
    optimized_composition = {
        comp: frac for comp, frac in zip(components, optimized_fractions)
    }

    # Create final state
    fluid = {comp: frac for comp, frac in zip(components, optimized_fractions)}
    final_state = State(fluid=fluid, T=T, p=p)

    return optimized_composition, final_state, result


def main():
    """Example usage of the optimization function."""

    print("Hydrocarbon Composition Optimization")
    print("=" * 50)

    # Initial composition (will be normalized)
    initial_composition = {
        "methane": 0.1,
        "ethane": 0.1,
        "propane": 0.1,
        "isobutane": 0.1,
        "n-butane": 0.1,
        "n-pentane": 0.1,
        "n-hexane": 0.1,
        "n-heptane": 0.1,
        "n-octane": 0.1,
        "nitrogen": 0.1,
        "carbon dioxide": 0.1,
    }
    components = list(initial_composition.keys())

    # Operating conditions
    T = Q_(37.78, "degC")
    p = Q_(17378.9, "kPa")

    # Target properties
    target_rho = Q_(156.682, "kg/m^3")  # Target density
    target_w = Q_(465.3, "m/s")  # Target velocity of sound
    target_cp = Q_(3.4123, "kJ/kg/K")  # Target cp
    target_cv = Q_(1.7974, "kJ/kg/K")  # Target cv
    target_z = 0.7861  # Target compressibility factor

    print(f"\nOperating Conditions:")
    print(f"  Temperature: {T}")
    print(f"  Pressure: {p}")

    print(f"\nTarget Properties:")
    print(f"  Density: {target_rho}")
    print(f"  Velocity of sound: {target_w}")
    print(f"  Cp: {target_cp}")
    print(f"  Cv: {target_cv}")
    print(f"  Compressibility factor (z): {target_z}")

    print(f"\nInitial Composition:")
    for comp, frac in initial_composition.items():
        print(f"  {comp}: {frac:.4f}")

    # Create initial state to show starting properties
    initial_state = State(fluid=initial_composition, T=T, p=p)
    print(f"\nInitial Properties:")
    print(f"  Density: {initial_state.rho():.3f}")
    print(f"  Velocity of sound: {initial_state.speed_sound():.3f}")

    # Run optimization
    print("\nOptimizing composition...")
    optimized_comp, final_state, result = optimize_composition(
        components,
        initial_composition,
        T,
        p,
        target_rho,
        target_w,
        target_cp,
        target_cv,
        target_z,
    )

    print(
        f"\nOptimization Result: {'Success' if result.success else 'Partial Success'}"
    )
    print(f"  Iterations: {result.nit}")
    print(f"  Final objective value: {result.fun:.6e}")

    print(f"\nOptimized Composition:")
    for comp, frac in optimized_comp.items():
        if frac > 1e-6:  # Only show components with significant fraction
            print(f"  {comp}: {frac:.6f}")

    print(f"\nFinal Properties:")
    final_cp = final_state.cp()
    final_cv = final_state.cv()
    final_z = final_state.z()

    print(f"  Density: {final_state.rho():.3f} (target: {target_rho})")
    print(f"  Velocity of sound: {final_state.speed_sound():.3f} (target: {target_w})")
    print(f"  Cp: {final_cp:.3f} (target: {target_cp})")
    print(f"  Cv: {final_cv:.3f} (target: {target_cv})")
    print(f"  Compressibility factor (z): {final_z:.4f} (target: {target_z})")

    # Calculate errors
    rho_error = abs((final_state.rho() - target_rho) / target_rho * 100)
    w_error = abs((final_state.speed_sound() - target_w) / target_w * 100)
    cp_error = abs((final_cp - target_cp) / target_cp * 100)
    cv_error = abs((final_cv - target_cv) / target_cv * 100)
    z_error = abs((final_z - target_z) / target_z * 100)

    print(f"\nRelative Errors:")
    print(f"  Density error: {rho_error.m_as('dimensionless'):.2f}%")
    print(f"  Velocity of sound error: {w_error.m_as('dimensionless'):.2f}%")
    print(f"  Cp error: {cp_error.m_as('dimensionless'):.2f}%")
    print(f"  Cv error: {cv_error.m_as('dimensionless'):.2f}%")
    print(f"  Z error: {z_error:.2f}%")

    return optimized_comp, final_state


if __name__ == "__main__":
    from scipy import optimize  # Import here to avoid issues when importing as module

    optimized_composition, final_state = main()