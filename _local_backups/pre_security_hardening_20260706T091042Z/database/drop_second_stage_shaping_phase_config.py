from database.audit_manager import AuditManager
from database.database import get_connection
from database.phase_template_manager import PhaseTemplateManager


SECOND_STAGE_TYPES = ("SECOND_STAGE", "SECONDSTAGE", "SS")


def main():
    PhaseTemplateManager.ensure_schema()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN")

        stage_rows = cursor.execute(
            """
            SELECT id
            FROM machine_stages
            WHERE UPPER(REPLACE(COALESCE(stage_type, ''), ' ', '_')) IN (
                'SECOND_STAGE',
                'SECONDSTAGE',
                'SS'
            )
            """
        ).fetchall()
        stage_ids = [row["id"] for row in stage_rows]

        if not stage_ids:
            conn.commit()
            print("No second-stage records found.")
            return

        placeholders = ",".join("?" for _ in stage_ids)

        cursor.execute(
            f"""
            UPDATE phase_control_group_master
            SET active = 0,
                description = 'Fixed in PLC logic; not recipe configurable'
            WHERE machine_stage_id IN ({placeholders})
                AND UPPER(COALESCE(phase_group_code, '')) = 'SHAPING_SIDE'
            """,
            stage_ids,
        )
        group_count = cursor.rowcount

        cursor.execute(
            f"""
            UPDATE phase_control_master
            SET active = 0,
                description = 'Fixed in PLC logic; not recipe configurable'
            WHERE machine_stage_id IN ({placeholders})
                AND UPPER(COALESCE(phase_group_code, '')) = 'SHAPING_SIDE'
            """,
            stage_ids,
        )
        option_count = cursor.rowcount

        recipe_phase_columns = {
            row["name"]
            for row in cursor.execute(
                "PRAGMA table_info(recipe_phase_control)"
            ).fetchall()
        }
        if "used" in recipe_phase_columns:
            cursor.execute(
                """
                UPDATE recipe_phase_control
                SET used = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE UPPER(COALESCE(phase_group_code, '')) = 'SHAPING_SIDE'
                    AND recipe_id IN (
                        SELECT r.id
                        FROM recipes r
                        INNER JOIN machine_stages s
                            ON s.id = r.stage_id
                        WHERE UPPER(REPLACE(COALESCE(s.stage_type, ''), ' ', '_')) IN (
                            'SECOND_STAGE',
                            'SECONDSTAGE',
                            'SS'
                        )
                    )
                """
            )
        else:
            cursor.execute(
                """
                DELETE FROM recipe_phase_control
                WHERE UPPER(COALESCE(phase_group_code, '')) = 'SHAPING_SIDE'
                    AND recipe_id IN (
                        SELECT r.id
                        FROM recipes r
                        INNER JOIN machine_stages s
                            ON s.id = r.stage_id
                        WHERE UPPER(REPLACE(COALESCE(s.stage_type, ''), ' ', '_')) IN (
                            'SECOND_STAGE',
                            'SECONDSTAGE',
                            'SS'
                        )
                    )
                """
            )
        recipe_row_count = cursor.rowcount

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    AuditManager.log_event(
        username="SYSTEM",
        role="SYSTEM",
        action="SECOND_STAGE_SHAPING_PHASE_FIXED",
        change_source="LOCAL_MIGRATION",
        parameter_name="SECOND_STAGE_PHASE_CONTROL_MODEL",
        old_value="CAP_STRIP_SIDE + BT_SIDE + SHAPING_SIDE configurable",
        new_value="CAP_STRIP_SIDE + BT_SIDE configurable; SHAPING_SIDE fixed in PLC",
        reason=(
            "Shaping head side sequence is fixed in machine PLC logic and "
            "must not be edited from CRS recipes."
        ),
    )

    print("Second-stage shaping phase-control cleanup complete.")
    print(f"Second-stage stages checked: {len(stage_ids)}")
    print(f"Shaping groups deactivated: {group_count}")
    print(f"Shaping phase options deactivated: {option_count}")
    print(f"Recipe shaping rows deactivated/removed: {recipe_row_count}")


if __name__ == "__main__":
    main()
