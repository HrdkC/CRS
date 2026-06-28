from database.database import get_connection


class PhaseControlManager:

    @staticmethod
    def create_phase_control(

        stage_type,

        phase_control_name,

        description=None,

        display_order=0

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id

            FROM phase_control_master

            WHERE

                stage_type = ?

                AND

                UPPER(phase_control_name)
                =
                UPPER(?)
            """,
            (

                stage_type,

                phase_control_name

            )
        )

        existing = cursor.fetchone()

        if existing:

            conn.close()

            print(
                f"Phase Already Exists : "
                f"{phase_control_name}"
            )

            return False

        cursor.execute(
            """
            INSERT INTO phase_control_master
            (

                stage_type,

                phase_control_name,

                description,

                display_order

            )
            VALUES
            (?, ?, ?, ?)
            """,
            (

                stage_type,

                phase_control_name,

                description,

                display_order

            )
        )

        conn.commit()

        conn.close()

        print(
            f"Phase Added : "
            f"{phase_control_name}"
        )

        return True

    @staticmethod
    def get_all_phase_controls():

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
    def get_phase_controls_by_stage(

        stage_type,

        machine_stage_id=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        if machine_stage_id:

            cursor.execute(
                """
                SELECT *

                FROM phase_control_master

                WHERE

                    active = 1

                    AND

                    UPPER(stage_type) = UPPER(?)

                    AND
                    (
                        machine_stage_id = ?

                        OR

                        machine_stage_id IS NULL
                    )

                ORDER BY
                    CASE COALESCE(phase_group_code, 'MAIN')
                        WHEN 'MAIN' THEN 0
                        WHEN 'CAP_STRIP_SIDE' THEN 1
                        WHEN 'BT_SIDE' THEN 2
                        WHEN 'SHAPING_SIDE' THEN 3
                        ELSE 99
                    END,
                    display_order,
                    phase_control_name
                """,
                (
                    stage_type,
                    machine_stage_id
                )
            )

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
                        WHEN 'SHAPING_SIDE' THEN 3
                        ELSE 99
                    END,
                    display_order,
                    phase_control_name
                """,
                (
                    stage_type,
                )
            )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]
