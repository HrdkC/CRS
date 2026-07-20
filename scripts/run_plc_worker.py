"""Durable CRS PLC operation worker.

Run this as a separately supervised Windows service/process. The Flask web
process only queues jobs; it never performs PLC writes.
"""

import os
import socket
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import ALLOW_PLC_COMMUNICATION, PLC_WORKER_ENABLED
from database.hardening_schema_manager import assert_v11_11_hardening_schema_ready
from database.plc_buffer_operation_manager import PLCBufferOperationManager
from database.plc_operation_job_manager import PLCOperationJobManager
from database.recipe_resource_lock_manager import RecipeResourceLockManager


def _heartbeat_loop(stop_event, job, worker_id):
    while not stop_event.wait(15):
        PLCOperationJobManager.heartbeat(job["id"], worker_id=worker_id)
        RecipeResourceLockManager.extend_lock(
            job.get("recipe_lock_id"), ttl_minutes=5
        )
        RecipeResourceLockManager.extend_lock(
            job.get("plc_lock_id"), ttl_minutes=5
        )


def run_worker(poll_seconds=2):
    if not PLC_WORKER_ENABLED:
        raise RuntimeError(
            "CRS_PLC_WORKER_ENABLED=1 is required to start the PLC worker."
        )
    if not ALLOW_PLC_COMMUNICATION:
        raise RuntimeError(
            "CRS_ALLOW_PLC_COMMUNICATION=YES is required. The worker is fail-closed."
        )

    assert_v11_11_hardening_schema_ready()
    recovered = PLCOperationJobManager.recover_stale_jobs(
        stale_minutes=int(os.getenv("CRS_PLC_JOB_STALE_MINUTES", "10")),
        recovery_reason="PLC_WORKER_STARTUP_RECOVERY",
    )
    worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    print(f"CRS PLC worker started: {worker_id}; recovered={recovered}", flush=True)

    while True:
        job = PLCOperationJobManager.claim_next_job(worker_id)
        if not job:
            time.sleep(max(1, int(poll_seconds)))
            continue

        stop_event = threading.Event()
        heartbeat_thread = threading.Thread(
            target=_heartbeat_loop,
            args=(stop_event, job, worker_id),
            daemon=True,
        )
        heartbeat_thread.start()

        try:
            PLCBufferOperationManager.run_operation(
                recipe_id=int(job["recipe_id"]),
                plc_id=int(job["plc_id"]),
                operation=job["operation"],
                username=job.get("started_by"),
                user_role=job.get("user_role"),
                status_job_id=job["id"],
            )
        except Exception as exc:
            PLCOperationJobManager.fail_job(
                job_id=job["id"],
                message=f"PLC worker operation failed: {type(exc).__name__}",
            )
        finally:
            stop_event.set()
            heartbeat_thread.join(timeout=2)
            RecipeResourceLockManager.release_lock(
                job.get("recipe_lock_id"), reason="PLC_OPERATION_COMPLETED"
            )
            RecipeResourceLockManager.release_lock(
                job.get("plc_lock_id"), reason="PLC_OPERATION_COMPLETED"
            )


if __name__ == "__main__":
    run_worker()
