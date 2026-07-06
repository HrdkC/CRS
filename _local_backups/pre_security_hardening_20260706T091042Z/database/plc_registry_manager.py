from database.database import (
    get_connection
)


class PLCRegistryManager:

    @staticmethod
    def create_plc(

        machine_stage_id,

        plc_name,

        ip_address,

        controller_type,

        firmware_revision="",

        program_revision="",

        processor_name="",

        plc_software="",

        description="",

        created_by=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO plc_registry
            (

                machine_stage_id,

                plc_name,

                ip_address,

                controller_type,

                firmware_revision,

                program_revision,

                processor_name,

                plc_software,

                description,

                created_by

            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (

                machine_stage_id,

                plc_name,

                ip_address,

                controller_type,

                firmware_revision,

                program_revision,

                processor_name,

                plc_software,

                description,

                created_by

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_all_plcs():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_registry

            ORDER BY plc_name
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_plc_by_id(

        plc_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_registry

            WHERE id = ?
            """,
            (
                plc_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def plc_name_exists(

        plc_name

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id

            FROM plc_registry

            WHERE UPPER(plc_name) = ?
            """,
            (
                plc_name.upper(),
            )
        )

        row = cursor.fetchone()

        conn.close()

        return row is not None

    @staticmethod
    def update_plc(

        plc_id,

        ip_address,

        controller_type,

        firmware_revision,

        program_revision,

        processor_name,

        plc_software,

        description

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_registry

            WHERE id = ?
            """,
            (
                plc_id,
            )
        )

        old_plc = cursor.fetchone()

        cursor.execute(
            """
            UPDATE plc_registry

            SET

                ip_address = ?,

                controller_type = ?,

                firmware_revision = ?,

                program_revision = ?,

                processor_name = ?,

                plc_software = ?,

                description = ?

            WHERE id = ?
            """,
            (

                ip_address,

                controller_type,

                firmware_revision,

                program_revision,

                processor_name,

                plc_software,

                description,

                plc_id

            )
        )

        conn.commit()

        conn.close()

        return dict(
            old_plc
        )

    @staticmethod
    def disable_plc(

        plc_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plc_registry

            SET active = 0

            WHERE id = ?
            """,
            (
                plc_id,
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def enable_plc(

        plc_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plc_registry

            SET active = 1

            WHERE id = ?
            """,
            (
                plc_id,
            )
        )

        conn.commit()

        conn.close()