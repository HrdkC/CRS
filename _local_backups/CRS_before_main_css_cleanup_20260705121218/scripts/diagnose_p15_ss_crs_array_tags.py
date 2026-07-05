import argparse
import os
import pprint
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

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
    row = cursor.execute(
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
        ORDER BY p.id DESC
        LIMIT 1
        """,
        (machine_code, normalized_stage),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _format_result(expression, result):
    error = getattr(result, "error", None)
    value = getattr(result, "value", None)
    if error:
        return f"FAIL {expression:<36} {error}"
    if isinstance(value, (list, tuple)):
        preview = list(value[:5]) if len(value) > 5 else list(value)
        return f"PASS {expression:<36} len={len(value)} preview={preview}"
    return f"PASS {expression:<36} value={value!r}"


def diagnose(machine="P15", stage="SS", tags=None):
    try:
        from pycomm3 import LogixDriver
    except Exception as ex:
        raise SystemExit(f"pycomm3 import failed: {ex}")

    plc = get_active_plc(machine, stage)
    if not plc:
        raise SystemExit(f"No active PLC configured in CRS database for {machine}/{stage}.")

    tags = tags or ["CRS_Recipe_Data", "CRS_Test_Recipe_Data"]
    print("=" * 90)
    print(f"CRS PLC ARRAY TAG DIAGNOSTIC: {machine}/{stage}")
    print(f"Active PLC from CRS DB: {plc.get('plc_name')} at {plc.get('ip_address')}")
    print("=" * 90)

    with LogixDriver(plc["ip_address"], init_tags=True, init_program_tags=False, timeout=10) as plc_conn:
        try:
            print("Controller info:")
            pprint.pprint(getattr(plc_conn, "info", None))
        except Exception:
            pass

        online_tags = getattr(plc_conn, "tags", {}) or {}
        print(f"Online controller tag count: {len(online_tags)}")
        crs_tags = [name for name in online_tags.keys() if str(name).upper().startswith("CRS_")]
        print(f"Online CRS_ controller tags found: {len(crs_tags)}")
        for name in crs_tags[:30]:
            print(f"  - {name}")
        if len(crs_tags) > 30:
            print(f"  ... {len(crs_tags) - 30} more")

        print("\nExact tag metadata:")
        for tag in tags:
            exact = online_tags.get(tag)
            if not exact:
                # Case-insensitive fallback
                exact_name = next((name for name in online_tags.keys() if str(name).upper() == tag.upper()), None)
                exact = online_tags.get(exact_name) if exact_name else None
                if exact_name:
                    print(f"  {tag}: FOUND as {exact_name}")
                else:
                    print(f"  {tag}: NOT FOUND in online controller tags")
            else:
                print(f"  {tag}: FOUND")
            if exact:
                pprint.pprint(exact)

        print("\nRead tests:")
        for tag in tags:
            expressions = [
                tag,
                f"{tag}{{5}}",
                f"{tag}[0]",
                f"{tag}[0]{{5}}",
                f"{tag}[149]",
            ]
            print(f"\nTag: {tag}")
            for expression in expressions:
                try:
                    result = plc_conn.read(expression)
                    print("  " + _format_result(expression, result))
                except Exception as ex:
                    print(f"  EXCEPTION {expression:<36} {ex}")

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description="Diagnose CRS REAL[150] array tags in the active PLC.")
    parser.add_argument("--machine", default="P15")
    parser.add_argument("--stage", default="SS")
    parser.add_argument("--tag", action="append", dest="tags", help="Additional/exact tag to test. Can be repeated.")
    args = parser.parse_args()
    diagnose(machine=args.machine, stage=args.stage, tags=args.tags)


if __name__ == "__main__":
    main()
