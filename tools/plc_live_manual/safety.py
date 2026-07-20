import os
import sys


def require_supervised_live_plc(tool_name):
    if os.getenv("CRS_ALLOW_LIVE_PLC_TESTS", "").strip().upper() != "YES":
        raise SystemExit(
            "Blocked: set CRS_ALLOW_LIVE_PLC_TESTS=YES only during an approved supervised PLC test."
        )
    if not sys.stdin.isatty():
        raise SystemExit("Blocked: supervised PLC tools require an interactive terminal.")
    expected = f"RUN LIVE PLC TOOL {os.path.basename(tool_name)}"
    print("WARNING: This tool may communicate with or modify a real PLC.")
    print(f"Type exactly: {expected}")
    if input("> ").strip() != expected:
        raise SystemExit("Confirmation did not match. No PLC action was started.")
