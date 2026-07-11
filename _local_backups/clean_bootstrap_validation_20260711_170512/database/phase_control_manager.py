from database.database import get_connection
from database.phase_template_manager import PhaseTemplateManager


class PhaseControlManager:

    @staticmethod
    def _is_first_stage(stage_type):
        return (
            str(stage_type or "").strip().upper().replace(" ", "_")
            in {"FIRST_STAGE", "FIRSTSTAGE", "FS"}
        )

    @staticmethod
    def _is_second_stage(stage_type):
        return (
            str(stage_type or "").strip().upper().replace(" ", "_")
            in {"SECOND_STAGE", "SECONDSTAGE", "SS"}
        )

    @staticmethod
    def create_phase_control(

        stage_type,

        phase_control_name,

        description=None,

        display_order=0

    ):

        conn = get_connection()

        cursor = conn.cursor()

        clean_name = PhaseTemplateManager.clean_display_name(phase_control_name)
        phase_key = PhaseTemplateManager.phase_key(clean_name)

        PhaseTemplateManager.ensure_schema()

        cursor.execute(
            """
            SELECT id

            FROM phase_control_master

            WHERE

                stage_type = ?

                AND

                UPPER(COALESCE(phase_control_key, phase_control_name))
                =
                UPPER(?)
            """,
            (

                stage_type,

                phase_key

            )
        )

        existing = cursor.fetchone()

        if existing:

            conn.close()

            print(
                f"Phase Already Exists : "
                f"{clean_name}"
            )

            return False

        cursor.execute(
            """
            INSERT INTO phase_control_master
            (

                stage_type,

                phase_control_name,

                phase_control_key,

                plc_phase_code,

                description,

                display_order

            )
            VALUES
            (?, ?, ?, ?, ?, ?)
            """,
            (

                stage_type,

                clean_name,

                phase_key,

                PhaseTemplateManager._phase_code_from_name("MAIN", clean_name, display_order),

                description,

                display_order

            )
        )

        conn.commit()

        conn.close()

        print(
            f"Phase Added : "
            f"{clean_name}"
        )

        return True

    @staticmethod
    def get_all_phase_controls():

        PhaseTemplateManager.ensure_schema()

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM phase_control_master

            WHERE active = 1

            ORDER BY

                stage_type,

                display_order
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def _unique_active_rows(rows):
        unique = []
        seen = set()
        for row in rows:
            data = dict(row)
            group_code = PhaseTemplateManager.group_code(
                data.get("phase_group_code")
            )
            phase_key = (
                data.get("phase_control_key")
                or
                PhaseTemplateManager.phase_key(
                    data.get("phase_control_name")
                )
            )
            key = (group_code, phase_key)
            if key in seen:
                continue
            seen.add(key)
            unique.append(data)
        return unique

    @staticmethod
    def get_phase_controls_by_stage(

        stage_type,

        machine_stage_id=None

    ):

        PhaseTemplateManager.ensure_schema()
        if machine_stage_id:
            PhaseTemplateManager.sync_phase_keys(machine_stage_id)

        conn = get_connection()

        cursor = conn.cursor()

        if machine_stage_id:
            cursor.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM phase_control_master
                WHERE
                    active = 1
                    AND UPPER(stage_type) = UPPER(?)
                    AND machine_stage_id = ?
                """,
                (
                    stage_type,
                    machine_stage_id,
                ),
            )
            has_stage_specific_rows = cursor.fetchone()["row_count"] > 0

            cursor.execute(
                """
                SELECT *

                FROM phase_control_master

                WHERE

                    active = 1

                    AND

                    UPPER(stage_type) = UPPER(?)

                    AND
                    machine_stage_id = ?

                ORDER BY
                    CASE COALESCE(phase_group_code, 'MAIN')
                        WHEN 'MAIN' THEN 0
                        WHEN 'CAP_STRIP_SIDE' THEN 1
                        WHEN 'BT_SIDE' THEN 2
                        ELSE 99
                    END,
                    display_order,
                    phase_control_name,
                    id
                """,
                (
                    stage_type,
                    machine_stage_id
                )
            )

            rows = cursor.fetchall()

            if not rows and not has_stage_specific_rows:
                cursor.execute(
                    """
                    SELECT *

                    FROM phase_control_master

                    WHERE

                        active = 1

                        AND

                        UPPER(stage_type) = UPPER(?)

                        AND machine_stage_id IS NULL

                    ORDER BY
                        CASE COALESCE(phase_group_code, 'MAIN')
                            WHEN 'MAIN' THEN 0
                            WHEN 'CAP_STRIP_SIDE' THEN 1
                            WHEN 'BT_SIDE' THEN 2
                            ELSE 99
                        END,
                        display_order,
                        phase_control_name,
                        id
                    """,
                    (
                        stage_type,
                    )
                )
                rows = cursor.fetchall()

        else:

            cursor.execute(
                """
                SELECT *

                FROM phase_control_master

                WHERE

                    active = 1

                    AND

                    UPPER(stage_type) = UPPER(?)

                ORDER BY
                    CASE COALESCE(phase_group_code, 'MAIN')
                        WHEN 'MAIN' THEN 0
                        WHEN 'CAP_STRIP_SIDE' THEN 1
                        WHEN 'BT_SIDE' THEN 2
                        ELSE 99
                    END,
                    display_order,
                    phase_control_name,
                    id
                """,
                (
                    stage_type,
                )
            )
            rows = cursor.fetchall()

        conn.close()

        if PhaseControlManager._is_first_stage(stage_type):
            rows = [
                row for row in rows
                if PhaseTemplateManager.group_code(row["phase_group_code"]) == "MAIN"
            ]

        if PhaseControlManager._is_second_stage(stage_type):
            rows = [
                row for row in rows
                if PhaseTemplateManager.group_code(row["phase_group_code"])
                in {"CAP_STRIP_SIDE", "BT_SIDE"}
            ]

        return PhaseControlManager._unique_active_rows(rows)
