import importlib
import time


def test_worker_heartbeat_becomes_online_and_then_stale(tmp_path, monkeypatch):
    module = importlib.import_module("utils.plc_worker_runtime_status")
    monkeypatch.setattr(module, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(module, "STATUS_PATH", tmp_path / "status.json")
    monkeypatch.setattr(module, "LOCK_PATH", tmp_path / "worker.lock")

    module.PLCWorkerRuntimeStatus.heartbeat(
        "worker-test", state="IDLE", poll_seconds=0.25
    )
    status = module.PLCWorkerRuntimeStatus.get_status(max_age_seconds=5)
    assert status["online"] is True
    assert status["state"] == "IDLE"
    assert status["poll_seconds"] == 0.25

    payload = module.PLCWorkerRuntimeStatus._read_json(module.STATUS_PATH)
    payload["updated_epoch"] = time.time() - 30
    module.PLCWorkerRuntimeStatus._atomic_write(module.STATUS_PATH, payload)
    assert module.PLCWorkerRuntimeStatus.get_status(max_age_seconds=5)["online"] is False


def test_singleton_rejects_second_fresh_worker(tmp_path, monkeypatch):
    module = importlib.import_module("utils.plc_worker_runtime_status")
    monkeypatch.setattr(module, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(module, "STATUS_PATH", tmp_path / "status.json")
    monkeypatch.setattr(module, "LOCK_PATH", tmp_path / "worker.lock")

    module.PLCWorkerRuntimeStatus.acquire_singleton("worker-one")
    module.PLCWorkerRuntimeStatus.heartbeat("worker-one")

    try:
        module.PLCWorkerRuntimeStatus.acquire_singleton("worker-two")
    except RuntimeError as exc:
        assert "already active" in str(exc)
    else:
        raise AssertionError("second worker was not rejected")

    module.PLCWorkerRuntimeStatus.mark_stopped("worker-one")
