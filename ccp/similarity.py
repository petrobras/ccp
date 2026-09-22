import numpy as np


def reynolds_limits(remsp):
    """Reynolds number envelope of ASME PTC 10-2022 (Fig. 3-3.5-1).

    Parameters
    ----------
    remsp : float
        Machine Reynolds number of the specified point.

    Returns
    -------
    lower, upper : float
        Limits on the test machine Reynolds number. Raises ``ValueError``
        below the 9e4 lower bound of the figure.
    """
    remsp = float(remsp)
    if remsp < 9e4:
        raise ValueError("Reynolds number out of specified range.")
    log_re = np.log10(remsp)
    if remsp < 8e5:
        upper = 10 ** (68.205 + 16.13 * log_re - 64.008 * np.sqrt(log_re))
    else:
        upper = remsp * 100
    if remsp < 5e5:
        lower = 10 ** (-22.733 - 4.247 * log_re + 21.63 * np.sqrt(log_re))
    else:
        lower = remsp * 0.1
    return lower, upper


def check_similarity(point_sp, point_t):
    """Function to check similarity between two different points.

    Parameters
    ----------
    point_sp : ccp.Point
        The specified (reference) point in the compressor map.
    point_t : ccp.Point
        The new point in the compressor map.

    Returns
    -------
    similarity_results : str
        Report with the flow coefficient, volume ratio, Mach and Reynolds
        similarity values and their PTC 10 limits (the Reynolds limits are the
        PTC 10-2022 envelope of :func:`reynolds_limits`, as ratios to the
        specified Reynolds number).
    """
    flow_coefficient = point_t.phi / point_sp.phi
    volume_ratio = point_t.volume_ratio / point_sp.volume_ratio
    mach = point_t.mach - point_sp.mach
    reynolds = point_t.reynolds / point_sp.reynolds

    flow_coefficient_limits = (0.96, 1.04)
    volume_ratio_limits = (0.95, 1.05)

    if 0 < point_sp.mach < 0.214:
        mach_limits = (-point_sp.mach.m, -0.25 * point_sp.mach.m + 0.286)
    elif 0.215 < point_sp.mach < 0.86:
        mach_limits = (0.266 * point_sp.mach.m - 0.271, -0.25 * point_sp.mach.m + 0.286)
    elif 0.86 < point_sp.mach:
        mach_limits = (-0.042, 0.07)
    else:
        mach_limits = "Mach outside PTC10 limits."

    remsp = float(point_sp.reynolds.m)
    try:
        lower, upper = reynolds_limits(remsp)
        reynolds_limits_ratio = (lower / remsp, upper / remsp)
    except ValueError:
        reynolds_limits_ratio = "Reynolds outside PTC10 limits."

    similarity_results = f"""
    {flow_coefficient.m:.3f} Limits -> {flow_coefficient_limits}
    {volume_ratio.m:.3f} Limits -> {volume_ratio_limits}
    {mach.m:.3f} Limits -> {mach_limits}
    {reynolds.m:.3f} Limits -> {reynolds_limits_ratio}
    """

    return similarity_results
