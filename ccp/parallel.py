"""Multiprocessing helpers.

REFPROP keeps process-global Fortran state, so worker pools must not be
created with fork(): a fork landing while any thread is inside the DLL (or
inside any other native library) hands every worker a torn copy of that
state, producing deadlocks and failed flash calculations. forkserver
workers fork from a clean, single-threaded server process instead; spawn
is used where forkserver is unavailable (Windows).
"""

import multiprocessing
import sys

_mp_context = None


def get_mp_context():
    """Multiprocessing context used for ccp worker pools.

    Returns
    -------
    context : multiprocessing.context.BaseContext
        A forkserver context preloaded with ccp (POSIX), or a spawn
        context on Windows.
    """
    global _mp_context
    if _mp_context is None:
        if sys.platform == "win32":
            _mp_context = multiprocessing.get_context("spawn")
        else:
            _mp_context = multiprocessing.get_context("forkserver")
            # Preload before the server starts so workers fork from a
            # process that has already paid the ccp import cost.
            _mp_context.set_forkserver_preload(["ccp"])
    return _mp_context
