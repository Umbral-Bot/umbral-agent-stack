from dispatcher import service as dispatcher_service

import pytest


class _FakeFcntl:
    LOCK_EX = 1
    LOCK_NB = 2
    LOCK_UN = 8

    def __init__(self, busy: bool = False):
        self.busy = busy
        self.calls = []

    def flock(self, _fileno: int, flags: int) -> None:
        self.calls.append(flags)
        if self.busy and flags == (self.LOCK_EX | self.LOCK_NB):
            raise BlockingIOError("lock busy")


def test_dispatcher_instance_lock_writes_pid_and_releases(monkeypatch, tmp_path):
    fake_fcntl = _FakeFcntl()
    lock_path = tmp_path / "dispatcher.lock"

    monkeypatch.setattr(dispatcher_service, "fcntl", fake_fcntl)
    monkeypatch.setattr(dispatcher_service.os, "getpid", lambda: 4242)

    lock = dispatcher_service.DispatcherInstanceLock(lock_path)
    acquired, owner_pid = lock.acquire()

    assert acquired is True
    assert owner_pid is None
    assert lock_path.read_text(encoding="utf-8") == "4242\n"

    lock.release()

    assert lock_path.read_text(encoding="utf-8") == ""
    assert fake_fcntl.calls == [fake_fcntl.LOCK_EX | fake_fcntl.LOCK_NB, fake_fcntl.LOCK_UN]


def test_dispatcher_instance_lock_returns_owner_pid_when_busy(monkeypatch, tmp_path):
    fake_fcntl = _FakeFcntl(busy=True)
    lock_path = tmp_path / "dispatcher.lock"
    lock_path.write_text("905580\n", encoding="utf-8")

    monkeypatch.setattr(dispatcher_service, "fcntl", fake_fcntl)

    lock = dispatcher_service.DispatcherInstanceLock(lock_path)
    acquired, owner_pid = lock.acquire()

    assert acquired is False
    assert owner_pid == 905580


def test_acquire_dispatcher_instance_lock_raises_with_owner_pid(monkeypatch, tmp_path):
    fake_fcntl = _FakeFcntl(busy=True)
    lock_path = tmp_path / "dispatcher.lock"
    lock_path.write_text("905626\n", encoding="utf-8")

    monkeypatch.setattr(dispatcher_service, "fcntl", fake_fcntl)
    monkeypatch.setenv("DISPATCHER_LOCK_PATH", str(lock_path))

    with pytest.raises(dispatcher_service.DispatcherInstanceError, match="905626"):
        dispatcher_service._acquire_dispatcher_instance_lock()
