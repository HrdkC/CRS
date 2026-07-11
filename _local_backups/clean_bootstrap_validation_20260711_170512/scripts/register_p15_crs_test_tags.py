import argparse
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.database import get_connection
from database.plc_crs_test_tag_definitions import get_tag_definitions
from database.plc_tag_manager import PLCTagManager

STAGE_ALIASES = {
    "FS": "FIRST_STAGE",
    "FIRST_STAGE": "FIRST_STAGE",
    "FIRST": "FIRST_STAGE",
    "FIRST STAGE": "FIRST_STAGE",
    "SS": "SECOND_STAGE",
    "SECOND_STAGE": "SECOND_STAGE",
    "SECOND": "SECOND_STAGE",
    "SECOND STAGE": "SECOND_STAGE",
}


def normalize_stage(stage):
    value = (stage or "").strip().upper().replace("-", "_")
    value = value.replace(" ", "_")
    if value == "BOTH":
        return "BOTH"
    return STAGE_ALIASES.get(value, value)


def resolve_contexts(machine_code, stage_arg):
    stage = normalize_stage(stage_arg)
    conn = get_connection()
    cursor = conn.cursor()
    params = [machine_code]
    where_stage = ""
    if stage != "BOTH":
        where_stage = "AND UPPER(s.stage_type) = UPPER(?)"
        params.append(stage)

    cursor.execute(
        f"""
        SELECT
            m.id AS machine_id,
            m.machine_code,
            s.id AS stage_id,
            s.stage_type,
            COALESCE(s.description, '') AS stage_description
        FROM tbm_machines m
        INNER JOIN machine_stages s ON s.machine_id = m.id
        WHERE
            UPPER(m.machine_code) = UPPER(?)
            {where_stage}
            AND COALESCE(m.active, 1) = 1
            AND COALESCE(s.active, 1) = 1
        ORDER BY s.id
        """,
        tuple(params),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def stage_short(stage_type):
    return "FS" if stage_type == "FIRST_STAGE" else "SS" if stage_type == "SECOND_STAGE" else stage_type


def register_tags(machine_code, stage_arg, created_by, include_optional=True):
    contexts = resolve_contexts(machine_code, stage_arg)
    if not contexts:
        raise SystemExit(f"No active machine/stage found for {machine_code}/{stage_arg}.")

    definitions = get_tag_definitions(include_optional=include_optional)
    total_created = 0
    total_updated = 0

    for ctx in contexts:
        print("=" * 80)
        print(
            f"Registering CRS PLC test tags for "
            f"{ctx['machine_code']} - {stage_short(ctx['stage_type'])} {ctx['stage_type'].replace('_', ' ').title()} "
            f"(machine_id={ctx['machine_id']}, stage_id={ctx['stage_id']})"
        )
        print("-" * 80)

        for tag in definitions:
            tag_id, created = PLCTagManager.upsert_tag(
                machine_id=ctx["machine_id"],
                stage_id=ctx["stage_id"],
                tag_name=tag["tag_name"],
                tag_type=tag["tag_type"],
                is_array=tag["is_array"],
                array_size=tag["array_size"],
                array_start_index=tag["array_start_index"],
                array_end_index=tag["array_end_index"],
                description=tag["description"],
                created_by=created_by,
                tag_purpose=tag["purpose"],
            )
            if created:
                total_created += 1
                status = "CREATED"
            else:
                total_updated += 1
                status = "UPDATED"
            print(f"{status:7} id={tag_id:<4} {tag['purpose']:<22} {tag['tag_name']}")

    print("=" * 80)
    print(f"Done. Created={total_created}, Updated={total_updated}")
    print(
        "Note: This registers tag names/purposes in CRS DB only. "
        "Actual PLC controller tags must already exist in Studio 5000."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Register standard P15 CRS PLC test tags in CRS database."
    )
    parser.add_argument("--machine", default="P15", help="Machine code. Default: P15")
    parser.add_argument(
        "--stage",
        default="BOTH",
        help="FS, SS, FIRST_STAGE, SECOND_STAGE, or BOTH. Default: BOTH",
    )
    parser.add_argument("--created-by", default="admin", help="Created-by username for new rows.")
    parser.add_argument(
        "--required-only",
        action="store_true",
        help="Register only the required buffer-operation tags.",
    )
    args = parser.parse_args()
    register_tags(
        machine_code=args.machine,
        stage_arg=args.stage,
        created_by=args.created_by,
        include_optional=not args.required_only,
    )


if __name__ == "__main__":
    main()
