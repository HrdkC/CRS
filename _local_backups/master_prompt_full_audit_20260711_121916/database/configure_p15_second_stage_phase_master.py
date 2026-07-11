from database.audit_manager import AuditManager
from database.database import get_connection
from database.phase_template_manager import PhaseTemplateManager


GROUPS = [
    ("CAP_STRIP_SIDE", "Cap Strip Side", "P15 second stage cap strip phase constants", 1),
    ("BT_SIDE", "B&T Side", "P15 second stage belt and tread phase constants", 2),
]


PHASES = {
    "CAP_STRIP_SIDE": [
        (101, 301, "APPLY CAP STRIP", "PLC Phase_Cntrl_constants_CapSd[0]"),
        (102, 302, "APPLY TREAD", "PLC Phase_Cntrl_constants_CapSd[1]"),
        (103, 0, "EMPTY PHASE", "Unused phase-control slot"),
    ],
    "BT_SIDE": [
        (201, 501, "APPLY BELT1", "PLC Phase_Cntrl_constants[1]"),
        (202, 502, "APPLY BELT2", "PLC Phase_Cntrl_constants[2]"),
        (203, 503, "TURN TABLE", "PLC Phase_Cntrl_constants[3]"),
        (204, 504, "BELT STITCHER", "PLC Phase_Cntrl_constants[4]"),
        (205, 505, "REMOVE BELTPACKAGE", "PLC Phase_Cntrl_constants[5]"),
        (206, 0, "EMPTY PHASE", "Unused phase-control slot"),
    ],
}


def _stage_context(cursor):
    row = cursor.execute(
        """
        SELECT
            m.id AS machine_id,
            m.machine_code,
            s.id AS stage_id,
            s.stage_type
        FROM tbm_machines m
        INNER JOIN machine_stages s
            ON s.machine_id = m.id
        WHERE m.machine_code = 'P15'
            AND UPPER(s.stage_type) IN ('SECOND_STAGE', 'SECONDSTAGE', 'SS')
        ORDER BY s.id
        LIMIT 1
        """
    ).fetchone()
    if not row:
        raise RuntimeError("P15 second stage is not available in machine_stages.")
    return dict(row)


def _ensure_group(cursor, stage_id, stage_type, code, name, description, order_no):
    existing = cursor.execute(
        """
        SELECT id
        FROM phase_control_group_master
        WHERE machine_stage_id = ?
            AND UPPER(phase_group_code) = UPPER(?)
        """,
        (stage_id, code),
    ).fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE phase_control_group_master
            SET
                stage_type = ?,
                phase_group_code = ?,
                phase_group_name = ?,
                description = ?,
                display_order = ?,
                active = 1
            WHERE id = ?
            """,
            (stage_type, code, name, description, order_no, existing["id"]),
        )
        return existing["id"]

    cursor.execute(
        """
        INSERT INTO phase_control_group_master
        (
            machine_stage_id,
            stage_type,
            phase_group_code,
            phase_group_name,
            description,
            display_order,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (stage_id, stage_type, code, name, description, order_no),
    )
    return cursor.lastrowid


def _upsert_phase(cursor, stage_id, stage_type, group_code, group_name, display_order, plc_code, name, description):
    key = PhaseTemplateManager.phase_key(name)
    existing = cursor.execute(
        """
        SELECT id
        FROM phase_control_master
        WHERE machine_stage_id = ?
            AND UPPER(COALESCE(phase_group_code, 'MAIN')) = UPPER(?)
            AND UPPER(COALESCE(phase_control_key, phase_control_name)) = UPPER(?)
        ORDER BY id
        LIMIT 1
        """,
        (stage_id, group_code, key),
    ).fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE phase_control_master
            SET
                stage_type = ?,
                phase_group_code = ?,
                phase_group_name = ?,
                phase_control_name = ?,
                phase_control_key = ?,
                plc_phase_code = ?,
                description = ?,
                display_order = ?,
                active = 1
            WHERE id = ?
            """,
            (
                stage_type,
                group_code,
                group_name,
                name,
                key,
                plc_code,
                description,
                display_order,
                existing["id"],
            ),
        )
        return existing["id"]

    cursor.execute(
        """
        INSERT INTO phase_control_master
        (
            machine_stage_id,
            stage_type,
            phase_group_code,
            phase_group_name,
            phase_control_name,
            phase_control_key,
            plc_phase_code,
            description,
            display_order,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            stage_id,
            stage_type,
            group_code,
            group_name,
            name,
            key,
            plc_code,
            description,
            display_order,
        ),
    )
    return cursor.lastrowid


def main():
    PhaseTemplateManager.ensure_schema()
    conn = get_connection()
    cursor = conn.cursor()
    context = _stage_context(cursor)
    stage_id = context["stage_id"]
    stage_type = context["stage_type"]

    desired_by_group = {
        group_code: {
            PhaseTemplateManager.phase_key(name)
            for _, _, name, _ in rows
        }
        for group_code, rows in PHASES.items()
    }

    try:
        cursor.execute("BEGIN")

        for group_code, group_name, description, order_no in GROUPS:
            _ensure_group(
                cursor,
                stage_id,
                stage_type,
                group_code,
                group_name,
                description,
                order_no,
            )

            for display_order, plc_code, name, phase_description in PHASES[group_code]:
                _upsert_phase(
                    cursor,
                    stage_id,
                    stage_type,
                    group_code,
                    group_name,
                    display_order,
                    plc_code,
                    name,
                    phase_description,
                )

        for group_code, wanted_keys in desired_by_group.items():
            placeholders = ",".join("?" for _ in wanted_keys)
            cursor.execute(
                f"""
                UPDATE phase_control_master
                SET active = 0,
                    description = COALESCE(NULLIF(description, ''), 'Deactivated by P15 SS PLC phase master alignment')
                WHERE machine_stage_id = ?
                    AND UPPER(COALESCE(phase_group_code, 'MAIN')) = UPPER(?)
                    AND UPPER(COALESCE(phase_control_key, phase_control_name)) NOT IN ({placeholders})
                """,
                tuple([stage_id, group_code] + sorted(wanted_keys)),
            )

        cursor.execute(
            """
            UPDATE phase_control_group_master
            SET active = 0,
                description = 'Fixed in PLC logic; not recipe configurable'
            WHERE machine_stage_id = ?
                AND UPPER(COALESCE(phase_group_code, '')) = 'SHAPING_SIDE'
            """,
            (stage_id,),
        )
        cursor.execute(
            """
            UPDATE phase_control_master
            SET active = 0,
                description = 'Fixed in PLC logic; not recipe configurable'
            WHERE machine_stage_id = ?
                AND UPPER(COALESCE(phase_group_code, '')) = 'SHAPING_SIDE'
            """,
            (stage_id,),
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    AuditManager.log_event(
        username="SYSTEM",
        role="SYSTEM",
        action="P15_SS_PHASE_MASTER_CONFIGURED",
        change_source="LOCAL_CONFIG_SCRIPT",
        record_id=str(stage_id),
        parameter_name="P15_SECOND_STAGE_PHASE_MASTER",
        old_value="Previous P15 SS eligible phase master",
        new_value="Configured exact PLC phase strings for Cap Strip and B&T groups only",
        reason="Shaping side sequence is fixed in PLC logic and not recipe configurable",
    )

    print("P15 second stage phase master configured.")
    print("Cap Strip Side: APPLY CAP STRIP, APPLY TREAD, EMPTY PHASE")
    print("B&T Side: APPLY BELT1, APPLY BELT2, TURN TABLE, BELT STITCHER, REMOVE BELTPACKAGE, EMPTY PHASE")
    print("Shaping Side: fixed in PLC logic; not recipe configurable")


if __name__ == "__main__":
    main()
