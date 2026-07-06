from database.database import get_connection
from database.stage_plc_tag_requirement_manager import StagePLCTagRequirementManager


LEGACY_SECOND_STAGE_PURPOSES = (
    "PHASE_CONTROL_STRING",
    "PHASE_STOP_STRING",
    "PHASE_POSITION_STRING",
)

TAG_NAME_PURPOSE_MAP = {
    "CRS_PHASE_CNTRL_STRING_CAPSD": "CAP_STRIP_PHASE_CONTROL_STRING",
    "CRS_PHASE_CONTROL_STRING_CAPSD": "CAP_STRIP_PHASE_CONTROL_STRING",
    "CRS_PHASE_CNTRL_STOP_STRING_CAPSD": "CAP_STRIP_PHASE_STOP_STRING",
    "CRS_PHASE_CONTROL_STOP_STRING_CAPSD": "CAP_STRIP_PHASE_STOP_STRING",
    "CRS_PHASE_CNTRL_STRING": "BT_PHASE_CONTROL_STRING",
    "CRS_PHASE_CONTROL_STRING": "BT_PHASE_CONTROL_STRING",
    "CRS_PHASE_CNTRL_STOP_STRING": "BT_PHASE_STOP_STRING",
    "CRS_PHASE_CONTROL_STOP_STRING": "BT_PHASE_STOP_STRING",
    "CRS_PHASE_CNTRL_POS_STRING": "BT_PHASE_POSITION_STRING",
    "CRS_PHASE_CNTRL_POSITION_STRING": "BT_PHASE_POSITION_STRING",
    "CRS_PHASE_CONTROL_POSITION_STRING": "BT_PHASE_POSITION_STRING",
}


def normalize(value):
    return str(value or "").strip().upper()


def main():
    conn = get_connection()
    cur = conn.cursor()
    stages = cur.execute(
        """
        SELECT
            s.id AS stage_id,
            s.machine_id,
            s.stage_type,
            m.machine_code
        FROM machine_stages s
        JOIN tbm_machines m ON m.id = s.machine_id
        WHERE UPPER(COALESCE(s.stage_type, '')) = 'SECOND_STAGE'
        """
    ).fetchall()
    conn.close()

    seeded = 0
    remapped = 0
    deactivated = 0

    for stage in stages:
        StagePLCTagRequirementManager.seed_stage_defaults(
            stage["machine_id"],
            stage["stage_id"],
        )
        seeded += 1

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE stage_plc_tag_requirements
            SET active = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE machine_id = ?
              AND stage_id = ?
              AND UPPER(purpose) IN (?, ?, ?)
            """,
            (
                stage["machine_id"],
                stage["stage_id"],
                *LEGACY_SECOND_STAGE_PURPOSES,
            ),
        )
        deactivated += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

        tags = cur.execute(
            """
            SELECT id, tag_name
            FROM plc_tags
            WHERE machine_id = ?
              AND stage_id = ?
            """,
            (
                stage["machine_id"],
                stage["stage_id"],
            ),
        ).fetchall()

        for tag in tags:
            purpose = TAG_NAME_PURPOSE_MAP.get(normalize(tag["tag_name"]))
            if not purpose:
                continue
            cur.execute(
                """
                UPDATE plc_tags
                SET tag_purpose = ?
                WHERE id = ?
                """,
                (purpose, tag["id"]),
            )
            remapped += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

        conn.commit()
        conn.close()

    print(
        "Second-stage phase tag migration complete: "
        f"{seeded} stage(s) seeded, "
        f"{deactivated} legacy rule(s) deactivated, "
        f"{remapped} saved PLC tag(s) remapped."
    )


if __name__ == "__main__":
    main()
