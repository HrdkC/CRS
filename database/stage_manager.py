from database.database import get_connection
from database.phase_control_default_manager import PhaseControlDefaultManager


class StageManager:

    @staticmethod
    def create_stage(

        machine_id,

        stage_type,

        description=""

    ):
        
        existing_stage_id = StageManager.get_stage_id(

            machine_id,

            stage_type

        )

        if existing_stage_id:

            print(

                f"{stage_type} Already Exists"

            )

            StageManager.ensure_phase_defaults(existing_stage_id, stage_type)

            return existing_stage_id

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO machine_stages
            (

                machine_id,

                stage_type,

                description

            )
            VALUES
            (?, ?, ?)
            """,
            (

                machine_id,

                stage_type,

                description

            )
        )

        stage_id = cursor.lastrowid

        conn.commit()

        conn.close()

        StageManager.ensure_phase_defaults(stage_id, stage_type)

        return stage_id

    @staticmethod
    def ensure_phase_defaults(stage_id, stage_type):
        try:
            PhaseControlDefaultManager.initialize_for_stage(
                stage_id,
                stage_type,
            )
        except Exception as exc:
            print(
                f"Phase defaults initialization skipped for {stage_type}: {exc}"
            )

    @staticmethod
    def get_machine_stages(

        machine_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM machine_stages

            WHERE machine_id = ?

            ORDER BY stage_type
            """,
            (
                machine_id,
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_all_stages():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                s.*,

                m.machine_code

            FROM machine_stages s

            LEFT JOIN tbm_machines m

            ON s.machine_id = m.id

            ORDER BY
                m.machine_code,
                s.stage_type
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_stage_by_id(

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM machine_stages

            WHERE id = ?
            """,
            (
                stage_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def disable_stage(

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE machine_stages

            SET active = 0

            WHERE id = ?
            """,
            (
                stage_id,
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def enable_stage(

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE machine_stages

            SET active = 1

            WHERE id = ?
            """,
            (
                stage_id,
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def stage_exists(

        machine_id,

        stage_type

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id

            FROM machine_stages

            WHERE

                machine_id = ?

                AND

                stage_type = ?
            """,
            (

                machine_id,

                stage_type

            )
        )

        row = cursor.fetchone()

        conn.close()

        return row is not None

    @staticmethod
    def get_stage_id(

        machine_id,

        stage_type

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id

            FROM machine_stages

            WHERE

                machine_id = ?

                AND

                stage_type = ?
            """,
            (

                machine_id,

                stage_type

            )
        )

        row = cursor.fetchone()

        conn.close()

        return row["id"] if row else None
    
    @staticmethod
    def get_all_stages_with_machine():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                s.*,

                m.machine_code

            FROM machine_stages s

            LEFT JOIN tbm_machines m

            ON s.machine_id = m.id

            ORDER BY

                m.machine_code,

                s.stage_type
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]
