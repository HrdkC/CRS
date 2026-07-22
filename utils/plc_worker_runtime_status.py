"""Runtime heartbeat and singleton guard for the durable CRS PLC worker.

This module deliberately uses small JSON files under ``instance`` so the Flask
web process can tell whether the separately supervised worker is alive before
it queues a PLC operation.  No PLC communication happens here.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


ROOT_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT_DIR / "instance"
STATUS_PATH = RUNTIME_DIR / "plc_worker_status.json"
LOCK_PATH = RUNTIME_DIR / "plc_worker.lock"


class PLCWorkerRuntimeStatus:
    DEFAULT_FRESH_SECONDS = 5.0

    @staticmethod
    def _ensure_dir() -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    @staticmethod
    def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
        PLCWorkerRuntimeStatus._ensure_dir()
        temp_path = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)

    @classmethod
    def get_status(cls, max_age_seconds: Optional[float] = None) -> Dict[str, Any]:
        max_age = float(
            cls.DEFAULT_FRESH_SECONDS if max_age_seconds is None else max_age_seconds
        )
        payload = cls._read_json(STATUS_PATH)
        updated_epoch = payload.get("updated_epoch")
        try:
            age_seconds = max(0.0, time.time() - float(updated_epoch))
        except (TypeError, ValueError):
            age_seconds = None

        online = bool(payload.get("worker_id")) and age_seconds is not None and age_seconds <= max_age
        payload["online"] = online
        payload["age_seconds"] = round(age_seconds, 3) if age_seconds is not None else None
        payload["status_path"] = str(STATUS_PATH)
        return payload

    @classmethod
    def heartbeat(
        cls,
        worker_id: str,
        *,
        state: str = "IDLE",
        current_job_id: Optional[str] = None,
        poll_seconds: Optional[float] = None,
    ) -> None:
        now = time.time()
        payload = {
            "worker_id": str(worker_id),
            "pid": os.getpid(),
            "state": str(state or "IDLE").upper(),
            "current_job_id": current_job_id,
            "poll_seconds": poll_seconds,
            "updated_epoch": now,
            "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        }
        cls._atomic_write(STATUS_PATH, payload)

    @classmethod
    def acquire_singleton(cls, worker_id: str, stale_after_seconds: float = 15.0) -> None:
        cls._ensure_dir()

        existing_status = cls.get_status(max_age_seconds=stale_after_seconds)
        if existing_status.get("online"):
            raise RuntimeError(
                "Another CRS PLC worker is already active: "
                + str(existing_status.get("worker_id"))
            )

        # A crashed process can leave the lock file behind.  It is safe to
        # remove only when no fresh heartbeat exists.
        if LOCK_PATH.exists():
            try:
                LOCK_PATH.unlink()
            except OSError as exc:
                raise RuntimeError(
                    "Unable to clear stale CRS PLC worker lock: " + str(exc)
                ) from exc

        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(str(LOCK_PATH), flags)
        except FileExistsError as exc:
            raise RuntimeError("Another CRS PLC worker is starting.") from exc

        try:
            payload = {
                "worker_id": str(worker_id),
                "pid": os.getpid(),
                "created_epoch": time.time(),
            }
            os.write(descriptor, json.dumps(payload).encode("utf-8"))
        finally:
            os.close(descriptor)

    @classmethod
    def release_singleton(cls, worker_id: str) -> None:
        lock_payload = cls._read_json(LOCK_PATH)
        if lock_payload and lock_payload.get("worker_id") not in (None, worker_id):
            return
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except OSError:
            pass

    @classmethod
    def mark_stopped(cls, worker_id: str) -> None:
        status = cls._read_json(STATUS_PATH)
        if status and status.get("worker_id") not in (None, worker_id):
            return
        status.update(
            {
                "worker_id": str(worker_id),
                "state": "STOPPED",
                "current_job_id": None,
                "updated_epoch": 0,
                "updated_utc": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())
                ),
            }
        )
        try:
            cls._atomic_write(STATUS_PATH, status)
        except OSError:
            pass
        cls.release_singleton(worker_id)
