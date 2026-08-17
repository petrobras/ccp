"""Multiprocessing helpers.

REFPROP keeps process-global Fortran state, so worker pools must not be
created with fork(): a fork landing while any thread is inside the DLL (or
inside any other native library) hands every worker a torn copy of that
state, producing deadlocks and failed flash calculations. forkserver
workers fork from a clean, single-threaded server process instead; spawn
is used where forkserver is unavailable (Windows).

Parallel execution is controlled globally:

- ``ccp.config.PARALLEL = False`` makes every ccp pool run serially in the
  current process — useful for debugging, small jobs and restricted
  environments (containers, sandboxes) where worker processes are
  expensive or unavailable.
- ``ccp.config.POOL_SIZE = 4`` caps the number of worker processes per
  pool; the default (``None``) is one worker per CPU.

The ``CCP_PARALLEL`` and ``CCP_POOL_SIZE`` environment variables override
the corresponding globals, so parallelism can be tuned without touching
code (e.g. ``CCP_PARALLEL=0`` in a container).
"""

import multiprocessing
import os
import sys
import time
from contextlib import contextmanager

from . import config

_mp_context = None

_FALSY = {"0", "false", "no", "off", ""}

_GUARD_MESSAGE = (
    "ccp worker processes are failing to start.\n"
    "The most common cause is a script that runs ccp multiprocessing "
    "(Impeller construction/conversion, Evaluation) at module top level: "
    "worker processes re-import the main module and recurse into pool "
    "creation. Guard the entry point with\n\n"
    "    if __name__ == '__main__':\n"
    "        ...\n\n"
    "or disable multiprocessing with ccp.config.PARALLEL = False (or the "
    "CCP_PARALLEL=0 environment variable)."
)


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


def parallel_enabled():
    """Whether ccp should use multiprocessing pools.

    Returns
    -------
    enabled : bool
        False if the CCP_PARALLEL environment variable is set to a falsy
        value ("0", "false", "no", "off") or, with the variable unset,
        if ``ccp.config.PARALLEL`` is False.
    """
    env = os.environ.get("CCP_PARALLEL")
    if env is not None:
        return env.strip().lower() not in _FALSY
    return bool(getattr(config, "PARALLEL", True))


def pool_size():
    """Number of worker processes for ccp pools.

    Returns
    -------
    size : int or None
        The CCP_POOL_SIZE environment variable if set, otherwise
        ``ccp.config.POOL_SIZE``. None means the multiprocessing default
        (one worker per CPU).
    """
    env = os.environ.get("CCP_POOL_SIZE", "").strip()
    if env:
        return max(1, int(env))
    size = getattr(config, "POOL_SIZE", None)
    if size is not None:
        return max(1, int(size))
    return None


def _start_timeout():
    env = os.environ.get("CCP_POOL_START_TIMEOUT", "").strip()
    return float(env) if env else 60.0


def _ping():
    return None


def _await_pool_ready(pool, processes, timeout):
    """Fail fast if pool workers die during startup.

    multiprocessing.Pool silently replaces dead workers forever, so a pool
    whose workers cannot start (typically a script missing the
    ``if __name__ == "__main__"`` guard) hangs indefinitely instead of
    raising. Watch a no-op task: if a full generation of workers is
    replaced, or the timeout expires, before it completes, abort with an
    actionable error.
    """
    result = pool.apply_async(_ping)
    deadline = time.monotonic() + timeout
    seen_workers = set()
    while True:
        try:
            result.get(timeout=0.5)
            return
        except multiprocessing.TimeoutError:
            pass
        seen_workers.update(p.pid for p in getattr(pool, "_pool", []))
        if len(seen_workers) >= 2 * processes or time.monotonic() >= deadline:
            raise RuntimeError(_GUARD_MESSAGE)


class _SerialPool:
    """Stand-in for the multiprocessing.Pool API ccp uses, running every
    task serially in the current process."""

    def map(self, func, iterable):
        return [func(item) for item in iterable]

    def imap(self, func, iterable):
        return (func(item) for item in iterable)


@contextmanager
def create_pool(processes=None):
    """Context manager yielding the worker pool used by ccp calculations.

    Honors ``ccp.config.PARALLEL``/``ccp.config.POOL_SIZE`` and the
    ``CCP_PARALLEL``/``CCP_POOL_SIZE`` environment variables: when parallel
    execution is disabled it yields a serial stand-in with the same
    ``map``/``imap`` API, so call sites need no branching. Worker startup
    is verified so that a script missing the ``if __name__ == "__main__"``
    guard raises an actionable RuntimeError instead of hanging forever.

    Parameters
    ----------
    processes : int, optional
        Number of worker processes. Defaults to ``pool_size()``.

    Yields
    ------
    pool
        A ``multiprocessing.pool.Pool`` or a serial stand-in.
    """
    if not parallel_enabled():
        yield _SerialPool()
        return
    if processes is None:
        processes = pool_size()
    if processes is None:
        processes = os.cpu_count() or 1
    try:
        pool = get_mp_context().Pool(processes)
    except RuntimeError as exc:
        # multiprocessing raises this in an unguarded child re-importing
        # the main module; replace it with an actionable message.
        if "bootstrapping phase" in str(exc):
            raise RuntimeError(_GUARD_MESSAGE) from exc
        raise
    with pool:
        _await_pool_ready(pool, processes, _start_timeout())
        yield pool
