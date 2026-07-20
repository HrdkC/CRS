import argparse
import os
import sys
import time
from datetime import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.plc_live_manual.safety import require_supervised_live_plc

from pycomm3 import LogixDriver

from database.database import get_connection

STAGE_ALIASES = {
    "FS": "FIRST_STAGE",
    "FIRST_STAGE": "FIRST_STAGE",
    "FIRST": "FIRST_STAGE",
    "SS": "SECOND_STAGE",
    "SECOND_STAGE": "SECOND_STAGE",
    "SECOND": "SECOND_STAGE",
}


def normalize_stage(stage):
    value = (stage or "").strip().upper().replace("-", "_").replace(" ", "_")
    return STAGE_ALIASES.get(value, value)


def get_active_plc(machine_code, stage):
    normalized_stage = normalize_stage(stage)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.*, m.machine_code, s.stage_type
        FROM plc_registry p
        INNER JOIN machine_stages s ON s.id = p.machine_stage_id
        INNER JOIN tbm_machines m ON m.id = s.machine_id
        WHERE
            UPPER(m.machine_code) = UPPER(?)
            AND UPPER(s.stage_type) = UPPER(?)
            AND COALESCE(p.active, 1) = 1
        ORDER BY p.id
        LIMIT 1
        """,
        (machine_code, normalized_stage),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def read_bool(plc_conn, tag_name):
    result = plc_conn.read(tag_name)
    error = getattr(result, "error", None)
    if error:
        raise RuntimeError(f"Read {tag_name} failed: {error}")
    return bool(getattr(result, "value", False))


def write_many(plc_conn, writes):
    for tag_name, value in writes:
        result = plc_conn.write((tag_name, value))
        error = getattr(result, "error", None)
        if error or not result or not bool(result):
            raise RuntimeError(f"Write {tag_name} failed: {error}")


def run(machine_code, stage, confirm, poll_seconds):
    if confirm != "YES":
        raise SystemExit(
            "Blocked. This script writes PLC handshake bits continuously. "
            "Run only for isolated test. Re-run with --confirm YES."
        )

    plc = get_active_plc(machine_code, stage)
    if not plc:
        raise SystemExit(f"No active PLC found for {machine_code}/{stage}.")

    print(f"Connecting to {plc['plc_name']} at {plc['ip_address']}...")
    print("Test handshake simulator running. Press CTRL+C to stop.")
    print("Behavior: Request TRUE -> Busy TRUE, Complete TRUE, Result=1. Request FALSE -> Busy/Complete FALSE.")

    with LogixDriver(plc["ip_address"], timeout=10) as plc_conn:
        write_many(
            plc_conn,
            [
                ("CRS_Download_Enable", True),
                ("CRS_Test_Machine_In_Manual", True),
                ("CRS_Download_Busy", False),
                ("CRS_Download_Complete", False),
                ("CRS_Download_Error", False),
                ("CRS_Download_Result", 0),
            ],
        )
        previous_request = None
        while True:
            request = read_bool(plc_conn, "CRS_Download_Request")
            if request != previous_request:
                print(f"{datetime.now().strftime('%H:%M:%S')} CRS_Download_Request={request}")
                previous_request = request

            if request:
                write_many(
                    plc_conn,
                    [
                        ("CRS_Download_Busy", True),
                        ("CRS_Download_Error", False),
                        ("CRS_Download_Result", 1),
                        ("CRS_Download_Complete", True),
                    ],
                )
            else:
                write_many(
                    plc_conn,
                    [
                        ("CRS_Download_Busy", False),
                        ("CRS_Download_Complete", False),
                    ],
                )
            time.sleep(max(0.1, poll_seconds))


def main():
    parser = argparse.ArgumentParser(
        description="PC-side test handshake simulator for CRS Download To PLC without PLC ladder changes."
    )
    parser.add_argument("--machine", default="P15", help="Machine code. Default: P15")
    parser.add_argument("--stage", required=True, help="FS or SS")
    parser.add_argument("--confirm", required=True, help="Must be YES")
    parser.add_argument("--poll-seconds", type=float, default=0.5, help="Polling interval. Default: 0.5")
    args = parser.parse_args()
    require_supervised_live_plc(__file__)
    run(args.machine, args.stage, args.confirm, args.poll_seconds)


if __name__ == "__main__":
    main()
