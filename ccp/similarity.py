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
    similarity_results : dict
        Dict with information on flow, volume ratio, Mach and Reynolds similarity.
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

    x = (point_sp.reynolds / 1e7) ** 0.3
    if 9e4 < point_sp.reynolds < 1e7:
        upper = 100 ** x
    elif 1e7 < point_sp.reynolds:
        upper = 100
    else:
        upper = "Reynolds outside PTC10 limits."

    if 9e4 < point_sp.reynolds < 1e6:
        lower = 0.01 ** x
    elif 1e6 < point_sp.reynolds:
        lower = 0.1
    else:
        lower = "Reynolds outside PTC10 limits."

    reynolds_limits = (lower, upper)

    similarity_results = f"""
    {flow_coefficient.m:.3f} Limits -> {flow_coefficient_limits}
    {volume_ratio.m:.3f} Limits -> {volume_ratio_limits}
    {mach.m:.3f} Limits -> {mach_limits}
    {reynolds.m:.3f} Limits -> {reynolds_limits}
    """

    return similarity_results
