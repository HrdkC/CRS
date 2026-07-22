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
from utils.plc_worker_runtime_status import PLCWorkerRuntimeStatus


def _heartbeat_loop(stop_event, job, worker_id):
    while not stop_event.wait(15):
        PLCOperationJobManager.heartbeat(job["id"], worker_id=worker_id)
        RecipeResourceLockManager.extend_lock(
            job.get("recipe_lock_id"), ttl_minutes=5
        )
        RecipeResourceLockManager.extend_lock(
            job.get("plc_lock_id"), ttl_minutes=5
        )


def run_worker(poll_seconds=None):
    if not PLC_WORKER_ENABLED:
        raise RuntimeError(
            "CRS_PLC_WORKER_ENABLED=1 is required to start the PLC worker."
        )
    if not ALLOW_PLC_COMMUNICATION:
        raise RuntimeError(
            "CRS_ALLOW_PLC_COMMUNICATION=YES is required. The worker is fail-closed."
        )

    if poll_seconds is None:
        poll_seconds = os.getenv("CRS_PLC_WORKER_POLL_SECONDS", "0.25")
    try:
        poll_seconds = float(poll_seconds)
    except (TypeError, ValueError):
        poll_seconds = 0.25
    poll_seconds = min(5.0, max(0.10, poll_seconds))

    assert_v11_11_hardening_schema_ready()
    recovered = PLCOperationJobManager.recover_stale_jobs(
        stale_minutes=int(os.getenv("CRS_PLC_JOB_STALE_MINUTES", "10")),
        recovery_reason="PLC_WORKER_STARTUP_RECOVERY",
    )
    worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    PLCWorkerRuntimeStatus.acquire_singleton(worker_id)
    PLCWorkerRuntimeStatus.heartbeat(
        worker_id, state="IDLE", poll_seconds=poll_seconds
    )
    print(
        f"CRS PLC worker started: {worker_id}; recovered={recovered}; "
        f"poll={poll_seconds:.2f}s",
        flush=True,
    )

    last_idle_heartbeat = 0.0
    try:
        while True:
            now = time.monotonic()
            if now - last_idle_heartbeat >= 1.0:
                PLCWorkerRuntimeStatus.heartbeat(
                    worker_id, state="IDLE", poll_seconds=poll_seconds
                )
                last_idle_heartbeat = now

            job = PLCOperationJobManager.claim_next_job(worker_id)
            if not job:
                time.sleep(poll_seconds)
                continue

            PLCWorkerRuntimeStatus.heartbeat(
                worker_id,
                state="RUNNING",
                current_job_id=job.get("id"),
                poll_seconds=poll_seconds,
            )
            print(
                f"Claimed PLC job {job.get('id')} ({job.get('operation')})",
                flush=True,
            )

            stop_event = threading.Event()
            heartbeat_thread = threading.Thread(
                target=_heartbeat_loop,
                args=(stop_event, job, worker_id),
                daemon=True,
            )
            heartbeat_thread.start()

            operation_result = None
            operation_error = None
            try:
                operation_result = PLCBufferOperationManager.run_operation(
                    recipe_id=int(job["recipe_id"]),
                    plc_id=int(job["plc_id"]),
                    operation=job["operation"],
                    username=job.get("started_by"),
                    user_role=job.get("user_role"),
                    status_job_id=job["id"],
                )
            except Exception as exc:
                operation_error = exc

            try:
                if operation_result is not None:
                    # The operation manager publishes progress throughout the
                    # PLC sequence. Persist the returned terminal result once
                    # more before releasing locks so a transient SQLite busy
                    # condition cannot leave the browser permanently at the
                    # last successful percentage (for example 93%) after the
                    # PLC write completed.
                    PLCOperationJobManager.ensure_terminal_state(
                        job_id=job["id"],
                        result=operation_result,
                    )
                else:
                    PLCOperationJobManager.fail_job(
                        job_id=job["id"],
                        message=(
                            "PLC worker operation failed: "
                            f"{type(operation_error).__name__}"
                        ),
                    )
            except Exception as status_exc:
                print(
                    "Unable to persist terminal PLC job state "
                    f"for {job.get('id')}: {status_exc}",
                    flush=True,
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
                PLCWorkerRuntimeStatus.heartbeat(
                    worker_id, state="IDLE", poll_seconds=poll_seconds
                )
                last_idle_heartbeat = time.monotonic()
    except KeyboardInterrupt:
        print("CRS PLC worker stopping...", flush=True)
    finally:
        PLCWorkerRuntimeStatus.mark_stopped(worker_id)


if __name__ == "__main__":
    run_worker()
