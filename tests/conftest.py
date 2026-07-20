import ipaddress
import os
import socket
import sys
import tempfile
from pathlib import Path

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def pytest_addoption(parser):
    parser.addoption(
        "--plc-live",
        action="store_true",
        default=False,
        help="Enable explicitly selected supervised PLC-live tests.",
    )


def pytest_configure(config):
    allow_live = (
        config.getoption("--plc-live")
        and os.getenv("CRS_ALLOW_LIVE_PLC_TESTS", "").strip().upper() == "YES"
    )
    os.environ["CRS_TEST_MODE"] = "0" if allow_live else "1"
    os.environ["CRS_ALLOW_STARTUP_MIGRATIONS"] = "1"
    os.environ.setdefault("CRS_PLC_JOB_RECOVERY_ON_STARTUP", "0")
    os.environ.setdefault("CRS_PLC_WORKER_ENABLED", "0")
    os.environ.setdefault("CRS_ALLOW_PLC_COMMUNICATION", "NO")
    test_db = Path(tempfile.gettempdir()) / f"crs_pytest_{os.getpid()}.db"
    if test_db.exists():
        test_db.unlink()
    os.environ.setdefault("CRS_DATABASE_PATH", str(test_db))

    if allow_live:
        return

    # Fail closed before test modules are imported.
    try:
        import pycomm3

        class BlockedLogixDriver:
            def __init__(self, *args, **kwargs):
                raise RuntimeError(
                    "Live PLC access is blocked during safe tests. Use the supervised "
                    "manual PLC tool with both --plc-live and CRS_ALLOW_LIVE_PLC_TESTS=YES."
                )

        pycomm3.LogixDriver = BlockedLogixDriver
    except ImportError:
        pass

    original_connect = socket.socket.connect

    def guarded_connect(sock, address):
        host = address[0] if isinstance(address, tuple) else str(address)
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(host))
        except Exception:
            ip = None
        if ip is not None and not ip.is_loopback:
            raise RuntimeError(
                f"External network connection blocked in safe tests: {host}"
            )
        return original_connect(sock, address)

    socket.socket.connect = guarded_connect


def pytest_collection_modifyitems(config, items):
    live_enabled = (
        config.getoption("--plc-live")
        and os.getenv("CRS_ALLOW_LIVE_PLC_TESTS", "").strip().upper() == "YES"
    )
    for item in items:
        path_text = str(item.fspath).replace("\\", "/")
        if "/tests/safe/" in path_text:
            item.add_marker(pytest.mark.safe)
        if item.get_closest_marker("plc_live") and not live_enabled:
            item.add_marker(
                pytest.mark.skip(
                    reason="PLC-live test requires --plc-live and CRS_ALLOW_LIVE_PLC_TESTS=YES"
                )
            )
