import multiprocessing

import pytest

import ccp
from ccp import parallel
from ccp.parallel import (
    _await_pool_ready,
    _SerialPool,
    create_pool,
    parallel_enabled,
    pool_size,
)


def test_parallel_enabled_default(monkeypatch):
    monkeypatch.delenv("CCP_PARALLEL", raising=False)
    assert parallel_enabled() is True


def test_parallel_enabled_config_global(monkeypatch):
    monkeypatch.delenv("CCP_PARALLEL", raising=False)
    monkeypatch.setattr(ccp.config, "PARALLEL", False)
    assert parallel_enabled() is False


@pytest.mark.parametrize("value", ["0", "false", "False", "no", "off", ""])
def test_parallel_enabled_env_falsy(monkeypatch, value):
    monkeypatch.setenv("CCP_PARALLEL", value)
    assert parallel_enabled() is False


def test_parallel_enabled_env_overrides_config(monkeypatch):
    monkeypatch.setenv("CCP_PARALLEL", "1")
    monkeypatch.setattr(ccp.config, "PARALLEL", False)
    assert parallel_enabled() is True


def test_pool_size_default(monkeypatch):
    monkeypatch.delenv("CCP_POOL_SIZE", raising=False)
    assert pool_size() is None


def test_pool_size_config_global(monkeypatch):
    monkeypatch.delenv("CCP_POOL_SIZE", raising=False)
    monkeypatch.setattr(ccp.config, "POOL_SIZE", 3)
    assert pool_size() == 3


def test_pool_size_env_overrides_config(monkeypatch):
    monkeypatch.setenv("CCP_POOL_SIZE", "2")
    monkeypatch.setattr(ccp.config, "POOL_SIZE", 8)
    assert pool_size() == 2


def test_serial_pool_map_and_imap():
    pool = _SerialPool()
    assert pool.map(str, [1, 2, 3]) == ["1", "2", "3"]
    assert list(pool.imap(str, [1, 2, 3])) == ["1", "2", "3"]


def test_create_pool_serial_when_disabled(monkeypatch):
    monkeypatch.setattr(ccp.config, "PARALLEL", False)
    with create_pool() as pool:
        assert isinstance(pool, _SerialPool)
        assert pool.map(abs, [-1, -2]) == [1, 2]


class _FakePool:
    """Records Pool construction and satisfies the create_pool protocol."""

    def __init__(self, processes):
        self.processes = processes

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeContext:
    def __init__(self):
        self.pools = []

    def Pool(self, processes):
        pool = _FakePool(processes)
        self.pools.append(pool)
        return pool


def test_create_pool_uses_configured_size(monkeypatch):
    monkeypatch.setattr(ccp.config, "POOL_SIZE", 3)
    context = _FakeContext()
    monkeypatch.setattr(parallel, "get_mp_context", lambda: context)
    monkeypatch.setattr(parallel, "_await_pool_ready", lambda *args: None)
    with create_pool() as pool:
        assert pool.processes == 3


def test_create_pool_explicit_processes_wins(monkeypatch):
    monkeypatch.setattr(ccp.config, "POOL_SIZE", 3)
    context = _FakeContext()
    monkeypatch.setattr(parallel, "get_mp_context", lambda: context)
    monkeypatch.setattr(parallel, "_await_pool_ready", lambda *args: None)
    with create_pool(processes=5) as pool:
        assert pool.processes == 5


def test_create_pool_translates_bootstrap_error(monkeypatch):
    class _BrokenContext:
        def Pool(self, processes):
            raise RuntimeError(
                "An attempt has been made to start a new process before the\n"
                "current process has finished its bootstrapping phase."
            )

    monkeypatch.setattr(parallel, "get_mp_context", lambda: _BrokenContext())
    with pytest.raises(RuntimeError, match="if __name__ == '__main__'"):
        with create_pool():
            pass


class _StuckResult:
    def get(self, timeout):
        raise multiprocessing.TimeoutError


class _DeadWorker:
    def __init__(self, pid):
        self.pid = pid
        self.exitcode = 1


class _ChurningPool:
    """A pool whose ping never completes."""

    def __init__(self, workers):
        self._pool = workers

    def apply_async(self, func):
        return _StuckResult()


def test_await_pool_ready_fails_fast_on_worker_churn():
    # Two distinct pids observed with processes=1 means a full worker
    # generation died and was replaced.
    pool = _ChurningPool([_DeadWorker(pid=1), _DeadWorker(pid=2)])
    with pytest.raises(RuntimeError, match="if __name__ == '__main__'"):
        _await_pool_ready(pool, processes=1, timeout=30)


def test_await_pool_ready_times_out():
    pool = _ChurningPool([_DeadWorker(pid=1)])
    with pytest.raises(RuntimeError, match="CCP_PARALLEL"):
        _await_pool_ready(pool, processes=4, timeout=0.6)


def test_await_pool_ready_returns_when_worker_responds():
    class _ReadyResult:
        def get(self, timeout):
            return None

    class _ReadyPool:
        _pool = []

        def apply_async(self, func):
            return _ReadyResult()

    _await_pool_ready(_ReadyPool(), processes=4, timeout=30)


@pytest.mark.slow
def test_create_pool_real_workers():
    with create_pool(processes=2) as pool:
        assert pool.map(abs, [-1, -2, -3]) == [1, 2, 3]
