import argparse
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.plc_live_manual.safety import require_supervised_live_plc

from pycomm3 import LogixDriver

from database.database import get_connection
from database.plc_crs_test_tag_definitions import get_tag_definitions

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
            s.id AS stage_id,
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


def read_value(plc_conn, tag):
    if tag["is_array"]:
        expression = f"{tag['tag_name']}{{{tag['array_size']}}}"
    else:
        expression = tag["tag_name"]
    result = plc_conn.read(expression)
    error = getattr(result, "error", None)
    value = getattr(result, "value", None)
    return expression, error, value


def verify(machine_code, stage, required_only=False):
    plc = get_active_plc(machine_code, stage)
    if not plc:
        raise SystemExit(f"No active PLC found for {machine_code}/{stage}.")

    tags = get_tag_definitions(include_optional=not required_only, stage_type=plc["stage_type"])
    print(f"Connecting to {plc['plc_name']} at {plc['ip_address']} for {machine_code}/{stage}...")

    ok_count = 0
    fail_count = 0
    with LogixDriver(plc["ip_address"], timeout=10) as plc_conn:
        for tag in tags:
            expression, error, value = read_value(plc_conn, tag)
            ok = not error
            detail = "OK"
            if ok and tag["is_array"]:
                try:
                    actual_len = len(list(value))
                except Exception:
                    actual_len = 0
                if actual_len < int(tag["array_size"]):
                    ok = False
                    detail = f"Array read length {actual_len}, expected {tag['array_size']}"
                else:
                    detail = f"OK, length={actual_len}"
            elif not ok:
                detail = str(error)

            if ok:
                ok_count += 1
                status = "PASS"
            else:
                fail_count += 1
                status = "FAIL"
            print(f"{status:4} {tag['purpose']:<22} {expression:<35} {detail}")

    print("-" * 80)
    print(f"Online verify completed. PASS={ok_count}, FAIL={fail_count}")
    if fail_count:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Verify P15 CRS test tags exist online in the selected PLC."
    )
    parser.add_argument("--machine", default="P15", help="Machine code. Default: P15")
    parser.add_argument("--stage", required=True, help="FS or SS")
    parser.add_argument(
        "--required-only",
        action="store_true",
        help="Verify only required buffer-operation tags.",
    )
    args = parser.parse_args()
    require_supervised_live_plc(__file__)
    verify(args.machine, args.stage, required_only=args.required_only)


if __name__ == "__main__":
    main()
