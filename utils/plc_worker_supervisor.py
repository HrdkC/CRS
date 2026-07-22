"""Automatic supervisor for the durable CRS PLC worker.

The Flask/Waitress web process remains separate from PLC execution, but when
``app.py`` is started directly this supervisor automatically starts, monitors,
and stops exactly one durable PLC worker.  Operators therefore do not need to
run a second command or BAT file.

No PLC connection is opened by this module.  The worker connects only after an
authorized PLC operation has been queued.
"""

from __future__ import annotations

import atexit
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from utils.plc_worker_runtime_status import PLCWorkerRuntimeStatus


ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
WORKER_SCRIPT = ROOT_DIR / "scripts" / "run_plc_worker.py"


def _env_enabled(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class PLCWorkerSupervisor:
    """Start and supervise one durable PLC worker subprocess."""

    def __init__(self) -> None:
        self.enabled = _env_enabled("CRS_AUTO_START_PLC_WORKER", "1")
        self.ready_timeout = max(
            2.0,
            float(os.getenv("CRS_PLC_WORKER_READY_TIMEOUT_SECONDS", "12")),
        )
        self.monitor_seconds = max(
            0.5,
            float(os.getenv("CRS_PLC_WORKER_MONITOR_SECONDS", "2")),
        )
        self.max_restart_attempts = max(
            0,
            int(os.getenv("CRS_PLC_WORKER_MAX_RESTARTS", "5")),
        )
        self.poll_seconds = min(
            5.0,
            max(0.10, float(os.getenv("CRS_PLC_WORKER_POLL_SECONDS", "0.25"))),
        )
        self._process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._started_by_supervisor = False
        self._log_handle = None
        self._restart_attempts = 0
        self._logger = logging.getLogger("crs.plc_worker_supervisor")
        atexit.register(self.stop)

    @property
    def process(self) -> Optional[subprocess.Popen]:
        return self._process

    def _open_log(self):
        if self._log_handle and not self._log_handle.closed:
            return self._log_handle
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = LOG_DIR / "plc_worker.log"
        self._log_handle = path.open("a", encoding="utf-8", buffering=1)
        return self._log_handle

    def _child_environment(self) -> dict[str, str]:
        child_env = os.environ.copy()
        child_env["CRS_PLC_WORKER_ENABLED"] = "1"
        child_env["CRS_ALLOW_PLC_COMMUNICATION"] = "YES"
        child_env["CRS_PLC_WORKER_POLL_SECONDS"] = f"{self.poll_seconds:g}"
        child_env["PYTHONUNBUFFERED"] = "1"
        return child_env

    def _spawn(self) -> None:
        if not WORKER_SCRIPT.exists():
            raise RuntimeError(f"PLC worker script not found: {WORKER_SCRIPT}")

        log_handle = self._open_log()
        creation_flags = 0
        if os.name == "nt":
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self._process = subprocess.Popen(
            [sys.executable, str(WORKER_SCRIPT)],
            cwd=str(ROOT_DIR),
            env=self._child_environment(),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        self._started_by_supervisor = True
        self._logger.info("Started durable PLC worker pid=%s", self._process.pid)

    def _wait_until_ready(self) -> bool:
        deadline = time.monotonic() + self.ready_timeout
        while time.monotonic() < deadline and not self._stop_event.is_set():
            status = PLCWorkerRuntimeStatus.get_status(max_age_seconds=5.0)
            if status.get("online"):
                return True
            if self._process is not None and self._process.poll() is not None:
                return False
            time.sleep(0.20)
        return False

    def start(self) -> dict:
        """Ensure one worker is online, then start the monitor thread."""
        if not self.enabled:
            return {
                "enabled": False,
                "online": False,
                "message": "Automatic PLC worker startup is disabled.",
            }

        current = PLCWorkerRuntimeStatus.get_status(max_age_seconds=5.0)
        if current.get("online"):
            self._started_by_supervisor = False
            self._start_monitor()
            return {
                "enabled": True,
                "online": True,
                "external": True,
                "worker_id": current.get("worker_id"),
                "message": "Existing durable PLC worker detected.",
            }

        self._spawn()
        if not self._wait_until_ready():
            exit_code = self._process.poll() if self._process is not None else None
            self.stop()
            raise RuntimeError(
                "The automatic durable PLC worker did not become ready within "
                f"{self.ready_timeout:g} seconds (exit_code={exit_code}). "
                "Check logs/plc_worker.log."
            )

        status = PLCWorkerRuntimeStatus.get_status(max_age_seconds=5.0)
        self._start_monitor()
        return {
            "enabled": True,
            "online": True,
            "external": False,
            "worker_id": status.get("worker_id"),
            "pid": self._process.pid if self._process else None,
            "message": "Durable PLC worker started automatically.",
        }

    def _start_monitor(self) -> None:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="crs-plc-worker-supervisor",
            daemon=True,
        )
        self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        while not self._stop_event.wait(self.monitor_seconds):
            if not self.enabled or self._stop_event.is_set():
                return

            status = PLCWorkerRuntimeStatus.get_status(max_age_seconds=5.0)
            process_exited = (
                self._process is not None and self._process.poll() is not None
            )
            if status.get("online") and not process_exited:
                self._restart_attempts = 0
                continue

            # Do not kill or replace another healthy worker that appeared.
            if status.get("online"):
                self._process = None
                self._started_by_supervisor = False
                self._restart_attempts = 0
                continue

            if self._restart_attempts >= self.max_restart_attempts:
                self._logger.error(
                    "PLC worker offline; automatic restart limit reached (%s).",
                    self.max_restart_attempts,
                )
                continue

            self._restart_attempts += 1
            delay = min(10.0, float(2 ** (self._restart_attempts - 1)))
            self._logger.warning(
                "PLC worker offline; restart attempt %s/%s in %.1fs.",
                self._restart_attempts,
                self.max_restart_attempts,
                delay,
            )
            if self._stop_event.wait(delay):
                return

            try:
                self._spawn()
                if self._wait_until_ready():
                    self._logger.info("PLC worker restarted successfully.")
                    self._restart_attempts = 0
                else:
                    self._logger.error("PLC worker restart did not become ready.")
            except Exception:
                self._logger.exception("PLC worker automatic restart failed.")

    def stop(self) -> None:
        """Stop only the worker process created by this supervisor."""
        if self._stop_event.is_set():
            return
        self._stop_event.set()

        process = self._process
        if self._started_by_supervisor and process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            except OSError:
                pass

        if (
            self._monitor_thread
            and self._monitor_thread.is_alive()
            and threading.current_thread() is not self._monitor_thread
        ):
            self._monitor_thread.join(timeout=3)

        if self._log_handle and not self._log_handle.closed:
            try:
                self._log_handle.flush()
                self._log_handle.close()
            except OSError:
                pass
