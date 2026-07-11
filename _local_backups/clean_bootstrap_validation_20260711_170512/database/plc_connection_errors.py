PLC_CONNECTION_REQUIRED_MESSAGE = (
    "PLC connection required. Local database access is still available, but this "
    "PLC function needs the selected PLC to be online."
)


def is_plc_connection_error(message):
    normalized = (message or "").lower()
    markers = [
        "failed to open a connection",
        "connection refused",
        "timed out",
        "timeout",
        "unreachable",
        "no route to host",
        "not connected",
        "connection reset",
        "socket",
        "cipconnectionerror",
        "commerror",
    ]
    return any(marker in normalized for marker in markers)


def format_plc_connection_failure(plc=None, detail=None, action="PLC function"):
    plc = plc or {}
    plc_name = plc.get("plc_name") or "selected PLC"
    plc_ip = plc.get("ip_address") or "unknown IP"

    message = (
        f"{action} needs PLC connection. CRS could not connect to "
        f"{plc_name} ({plc_ip}). Local database access remains available."
    )

    if detail:
        message += f" Technical detail: {detail}"

    return message
