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

        stage_type

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM phase_control_master

            WHERE

                active = 1

                AND

                stage_type = ?

            ORDER BY
                display_order
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