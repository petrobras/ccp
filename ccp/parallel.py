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

The ``CCP_PARALLEL`` and ``CCP_POOL_SIZE`` environment variables, when set
to a non-empty value, override the corresponding globals, so parallelism
can be tuned without touching code (e.g. ``CCP_PARALLEL=0`` in a
container). ``CCP_POOL_START_TIMEOUT`` (seconds, default 60) bounds how
long a pool may take to start its workers before ccp gives up — raise it
on machines where worker startup (one ccp + REFPROP import per worker) is
slow.
"""

import multiprocessing
import os
import sys
import time
from contextlib import contextmanager

from . import config

_mp_context = None

_FALSY = {"0", "false", "no", "off"}

_GUARD_MESSAGE = (
    "ccp worker processes are dying during startup.\n"
    "The most common cause is a script that runs ccp multiprocessing "
    "(Impeller construction/conversion, Evaluation) at module top level: "
    "worker processes re-import the main module and recurse into pool "
    "creation. Guard the entry point with\n\n"
    "    if __name__ == '__main__':\n"
    "        ...\n\n"
    "or disable multiprocessing with ccp.config.PARALLEL = False (or the "
    "CCP_PARALLEL=0 environment variable)."
)

_TIMEOUT_MESSAGE = (
    "ccp worker pool startup timed out after {timeout:.0f} s.\n"
    "The workers are alive but slow to start (each one imports ccp and "
    "loads REFPROP), which can happen on cold starts and heavily loaded "
    "machines. Raise the deadline with the CCP_POOL_START_TIMEOUT "
    "environment variable (seconds), lower the worker count with "
    "ccp.config.POOL_SIZE (or CCP_POOL_SIZE), or disable multiprocessing "
    "with ccp.config.PARALLEL = False (or CCP_PARALLEL=0)."
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
        value ("0", "false", "no", "off") or, with the variable unset or
        empty, if ``ccp.config.PARALLEL`` is False.
    """
    env = os.environ.get("CCP_PARALLEL", "").strip()
    if env:
        return env.lower() not in _FALSY
    return bool(config.PARALLEL)


def _positive_int(value, source):
    try:
        size = int(value)
    except (TypeError, ValueError):
        size = 0
    if size < 1:
        raise ValueError(f"{source} must be a positive integer, got {value!r}")
    return size


def pool_size():
    """Number of worker processes for ccp pools.

    Returns
    -------
    size : int or None
        The CCP_POOL_SIZE environment variable if set to a non-empty
        value, otherwise ``ccp.config.POOL_SIZE``. None means one worker
        per CPU available to this process.

    Raises
    ------
    ValueError
        If the configured value is not a positive integer.
    """
    env = os.environ.get("CCP_POOL_SIZE", "").strip()
    if env:
        return _positive_int(env, "the CCP_POOL_SIZE environment variable")
    size = config.POOL_SIZE
    if size is not None:
        return _positive_int(size, "ccp.config.POOL_SIZE")
    return None


def _start_timeout():
    env = os.environ.get("CCP_POOL_START_TIMEOUT", "").strip()
    if not env:
        return 60.0
    try:
        timeout = float(env)
    except ValueError:
        timeout = 0.0
    if not timeout > 0:
        raise ValueError(
            "the CCP_POOL_START_TIMEOUT environment variable must be a "
            f"positive number of seconds, got {env!r}"
        )
    return timeout


def _ping():
    return None


def _await_pool_ready(pool, processes, timeout):
    """Fail fast if pool workers die during startup.

    multiprocessing.Pool silently replaces dead workers forever, so a pool
    whose workers cannot start (typically a script missing the
    ``if __name__ == "__main__"`` guard) hangs indefinitely instead of
    raising. Watch a no-op task: if two full generations of workers die
    before it completes, abort with the missing-guard error; if the
    deadline expires with workers still alive, abort with a slow-start
    error instead. A single worker death is tolerated so that a transient
    failure (e.g. one worker OOM-killed) is not misdiagnosed as a missing
    guard.
    """
    result = pool.apply_async(_ping)
    deadline = time.monotonic() + timeout
    dead_workers = set()
    while True:
        try:
            result.get(timeout=0.5)
            return
        except multiprocessing.TimeoutError:
            pass
        dead_workers.update(p.pid for p in pool._pool if p.exitcode is not None)
        if len(dead_workers) >= 2 * processes:
            raise RuntimeError(_GUARD_MESSAGE)
        if time.monotonic() >= deadline:
            raise RuntimeError(_TIMEOUT_MESSAGE.format(timeout=timeout))


class _SerialPool:
    """Stand-in for the multiprocessing.Pool API ccp uses, running every
    task serially in the current process."""

    def map(self, func, iterable):
        return [func(item) for item in iterable]

    def imap(self, func, iterable):
        return (func(item) for item in iterable)


_startup_verified = False


@contextmanager
def create_pool(processes=None, parallel=None):
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
    parallel : bool, optional
        False forces a serial pool (a call site's explicit debugging
        switch). The default (None) follows ``parallel_enabled()``; True
        does not override a global disable.

    Yields
    ------
    pool
        A ``multiprocessing.pool.Pool`` or a serial stand-in.
    """
    if parallel is False or not parallel_enabled():
        yield _SerialPool()
        return
    if processes is None:
        processes = pool_size()
    if processes is None:
        # process_cpu_count (3.13+) respects CPU affinity, e.g. in
        # cpuset-limited containers.
        processes = getattr(os, "process_cpu_count", os.cpu_count)() or 1
    try:
        pool = get_mp_context().Pool(processes)
    except RuntimeError as exc:
        # multiprocessing raises this in an unguarded child re-importing
        # the main module; replace it with an actionable message.
        if "bootstrapping phase" in str(exc):
            raise RuntimeError(_GUARD_MESSAGE) from exc
        raise
    with pool:
        # The missing-guard failure is deterministic per process, so one
        # verified startup proves later pools cannot hit it — skip the
        # blocking readiness check after the first success.
        global _startup_verified
        if not _startup_verified:
            _await_pool_ready(pool, processes, _start_timeout())
            _startup_verified = True
        yield pool
