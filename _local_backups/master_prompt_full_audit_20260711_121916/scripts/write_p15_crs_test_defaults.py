import argparse
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from pycomm3 import LogixDriver

from database.database import get_connection
from database.plc_crs_test_tag_definitions import PAYLOAD_SIZE

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
        SELECT
            p.*,
            m.machine_code,
            s.stage_type
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


def write_defaults(machine_code, stage, confirm, zero_arrays=False):
    if confirm != "YES":
        raise SystemExit("Blocked. Re-run with --confirm YES after confirming PLC is in safe test/manual condition.")

    plc = get_active_plc(machine_code, stage)
    if not plc:
        raise SystemExit(f"No active PLC found for {machine_code}/{stage}.")

    scalar_writes = [
        ("CRS_Download_Enable", True),
        ("CRS_Test_Machine_In_Manual", True),
        ("CRS_Download_Request", False),
        ("CRS_Download_Complete", False),
        ("CRS_Download_Ack", False),
        ("CRS_Download_Busy", False),
        ("CRS_Download_Error", False),
        ("CRS_Download_OS", False),
        ("CRS_Download_Result", 0),
        ("CRS_Recipe_Code", "TEST"),
        ("CRS_Last_Download_Time", ""),
        ("CRS_Last_Download_User", ""),
        ("CRS_Test_Recipe_No", 0),
        ("CRS_Test_Length", 0.0),
        ("CRS_Test_Width", 0.0),
        ("CRS_Test_Speed", 0.0),
    ]

    print(f"Connecting to {plc['plc_name']} at {plc['ip_address']}...")
    with LogixDriver(plc["ip_address"], timeout=10) as plc_conn:
        for tag_name, value in scalar_writes:
            result = plc_conn.write((tag_name, value))
            error = getattr(result, "error", None)
            status = "OK" if result and not error and bool(result) else f"FAILED: {error}"
            print(f"WRITE {tag_name:<30} {value!r:<12} {status}")

        if zero_arrays:
            zeros = [0.0] * PAYLOAD_SIZE
            for tag_name in ["CRS_Recipe_Data", "CRS_Test_Recipe_Data"]:
                expression = f"{tag_name}{{{PAYLOAD_SIZE}}}"
                result = plc_conn.write((expression, zeros))
                error = getattr(result, "error", None)
                status = "OK" if result and not error and bool(result) else f"FAILED: {error}"
                print(f"WRITE {expression:<30} REAL[{PAYLOAD_SIZE}] {status}")

    print("Done. Test permissives set TRUE; handshake bits cleared.")


def main():
    parser = argparse.ArgumentParser(
        description="Write safe test default values to P15 CRS PLC test tags."
    )
    parser.add_argument("--machine", default="P15", help="Machine code. Default: P15")
    parser.add_argument("--stage", required=True, help="FS or SS")
    parser.add_argument("--confirm", required=True, help="Must be YES")
    parser.add_argument(
        "--zero-arrays",
        action="store_true",
        help="Also write 150 zeroes to CRS_Recipe_Data and CRS_Test_Recipe_Data.",
    )
    args = parser.parse_args()
    write_defaults(args.machine, args.stage, args.confirm, zero_arrays=args.zero_arrays)


if __name__ == "__main__":
    main()
