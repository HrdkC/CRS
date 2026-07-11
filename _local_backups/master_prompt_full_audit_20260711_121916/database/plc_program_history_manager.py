from database.database import (
    get_connection
)


class PLCProgramHistoryManager:

    @staticmethod
    def create_history(

        plc_id,

        old_program_revision,

        new_program_revision,

        username

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO plc_program_history
            (

                plc_registry_id,

                old_program_revision,

                new_program_revision,

                changed_by

            )
            VALUES
            (?, ?, ?, ?)
            """,
            (

                plc_id,

                old_program_revision,

                new_program_revision,

                username

            )
        )

        conn.commit()

        conn.close()