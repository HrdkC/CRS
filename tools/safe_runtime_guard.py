"""Install fail-closed network/PLC guards for verification tools."""

import ipaddress
import socket


def install_safe_runtime_guard():
    try:
        import pycomm3

        class BlockedLogixDriver:
            def __init__(self, *args, **kwargs):
                raise RuntimeError(
                    "PLC communication is blocked in CRS safe verification."
                )

        pycomm3.LogixDriver = BlockedLogixDriver
    except ImportError:
        pass

    original_connect = socket.socket.connect
    if getattr(original_connect, "_crs_safe_guard", False):
        return

    def guarded_connect(sock, address):
        host = address[0] if isinstance(address, tuple) else str(address)
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(host))
        except Exception:
            ip = None
        if ip is not None and not ip.is_loopback:
            raise RuntimeError(f"External network blocked by CRS safe guard: {host}")
        return original_connect(sock, address)

    guarded_connect._crs_safe_guard = True
    socket.socket.connect = guarded_connect
