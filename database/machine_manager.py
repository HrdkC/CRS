from database.database import get_connection

from database.stage_manager import (
    StageManager
)

from database.tbm_family_manager import (
    TBMFamilyManager
)


class MachineManager:

    @staticmethod
    def create_machine(

        machine_code,

        family_id,

        description="",

        created_by=None

    ):

        if not machine_code:
            raise ValueError("Machine code is required.")

        machine_code = (
            machine_code
            .strip()
            .upper()
        )

        if not machine_code:
            raise ValueError("Machine code is required.")

        family = TBMFamilyManager.get_family_by_id(family_id)

        if not family:
            raise ValueError("Selected TBM family was not found.")

        if family.get("active") != 1:
            raise ValueError("Selected TBM family is disabled.")

        conn = get_connection()

        cursor = conn.cursor()

        if MachineManager.machine_code_exists(
            machine_code
        ):

            raise ValueError(
                f"Machine {machine_code} already exists"
            )

        cursor.execute(
            """
            INSERT INTO tbm_machines
            (

                machine_code,

                family_id,

                description,

                created_by

            )
            VALUES
            (?, ?, ?, ?)
            """,
            (

                machine_code,

                family_id,

                description,

                created_by

            )
        )

        machine_id = cursor.lastrowid

        conn.commit()

        conn.close()

        if not StageManager.stage_exists(
            machine_id,
            "FIRST_STAGE"
        ):

            StageManager.create_stage(

                machine_id=machine_id,

                stage_type="FIRST_STAGE",

                description="First Stage"

            )

        if not StageManager.stage_exists(
            machine_id,
            "SECOND_STAGE"
        ):

            StageManager.create_stage(

                machine_id=machine_id,

                stage_type="SECOND_STAGE",

                description="Second Stage"

            )

    @staticmethod
    def get_all_machines():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                m.*,

                f.family_name

            FROM tbm_machines m

            LEFT JOIN tbm_families f

            ON m.family_id = f.id

            ORDER BY m.machine_code
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_machine_by_id(

        machine_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM tbm_machines

            WHERE id = ?
            """,
            (
                machine_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def get_machine_with_family_by_id(

        machine_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                m.*,
                f.family_name
            FROM tbm_machines m
            LEFT JOIN tbm_families f
            ON m.family_id = f.id
            WHERE m.id = ?
            """,
            (
                machine_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None
    
    @staticmethod
    def machine_code_exists(

        machine_code,

        exclude_machine_id=None

    ):

        machine_code = (machine_code or "").strip().upper()

        if not machine_code:

            return False

        conn = get_connection()

        cursor = conn.cursor()

        if exclude_machine_id:

            cursor.execute(
                """
                SELECT id

                FROM tbm_machines

                WHERE machine_code = ?

                AND id <> ?
                """,
                (
                    machine_code,

                    exclude_machine_id
                )
            )

        else:

            cursor.execute(
                """
                SELECT id

                FROM tbm_machines

                WHERE machine_code = ?
                """,
                (
                    machine_code,
                )
            )

        row = cursor.fetchone()

        conn.close()

        return row is not None

    @staticmethod
    def update_machine(

        machine_id,

        machine_code,

        family_id,

        description

    ):

        machine_code = (machine_code or "").strip().upper()

        if not machine_code:
            raise ValueError("Machine code is required.")

        if MachineManager.machine_code_exists(
            machine_code,
            exclude_machine_id=machine_id
        ):

            raise ValueError(f"Machine {machine_code} already exists.")

        family = TBMFamilyManager.get_family_by_id(family_id)

        if not family:
            raise ValueError("Selected TBM family was not found.")

        if family.get("active") != 1:
            raise ValueError("Selected TBM family is disabled.")

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_machines

            SET

                machine_code = ?,

                family_id = ?,

                description = ?

            WHERE id = ?
            """,
            (

                machine_code,

                family_id,

                description,

                machine_id

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def reassign_family(

        machine_id,

        family_id

    ):

        current = MachineManager.get_machine_with_family_by_id(machine_id)

        if not current:
            raise ValueError("Machine record was not found.")

        family = TBMFamilyManager.get_family_by_id(family_id)

        if not family:
            raise ValueError("Selected TBM family was not found.")

        if family.get("active") != 1:
            raise ValueError("Selected TBM family is disabled.")

        if str(current.get("family_id")) == str(family_id):
            raise ValueError(
                f"Machine {current['machine_code']} is already linked "
                f"to {family['family_name']}."
            )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_machines

            SET family_id = ?

            WHERE id = ?
            """,
            (
                family_id,
                machine_id
            )
        )

        conn.commit()

        conn.close()

        updated = MachineManager.get_machine_with_family_by_id(machine_id)

        return {
            "old": current,
            "new": updated
        }

    @staticmethod
    def disable_machine(

        machine_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_machines

            SET active = 0

            WHERE id = ?
            """,
            (
                machine_id,
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def enable_machine(

        machine_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_machines

            SET active = 1

            WHERE id = ?
            """,
            (
                machine_id,
            )
        )

        conn.commit()

        conn.close()
