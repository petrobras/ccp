.. currentmodule:: ccp.point

Performance Functions
=====================

These functions are available in the ccp.point module and they are mainly used
by the ccp.Point class in the performance calculation.

.. automodule:: ccp.point
    :members:
        head_isentropic,
        head_pol_mallen_saville,
        head_pol_sandberg_colby,
        head_pol_schultz,
        head_pol_huntington,
        head_pol_sandberg_colby_multistep,
        head_pol,
        head_reference,
        head_reference_2017,
        eff_isentropic,
        eff_pol_mallen_saville,
        eff_pol_sandberg_colby,
        eff_pol_schultz,
        eff_pol_huntington,
        eff_pol_sandberg_colby_multistep,
        eff_pol,
        f_schultz,
        f_sandberg_colby,
        disch_from_suc_head_eff,
        disch_from_suc_disch_p_eff,
        disch_from_suc_disch_T_head,
        disch_from_suc_volume_ratio_eff,
        isentropic_disch_from_rho,
        flow_from_phi,
        head_from_psi,
        mach,
        n_exp,
        phi,
        power_calc,
        reynolds,
        speed_from_psi,
        u_calc,

Solvers
-------

The discharge closures above reduce to one monotone equation in a pressure or
a temperature, bracketed by the suction and the isentropic discharge, and are
solved with:

.. automodule:: ccp.roots
    :members: solve_monotone

Similarity
----------

.. automodule:: ccp.similarity
    :members: check_similarity, reynolds_limits

.. bibliography::
    :filter: docname in docnames
