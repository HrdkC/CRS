from database.database import get_connection


class TemplateManager:

    @staticmethod
    def create_template(

        machine_stage_id,

        template_name,

        description=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO template_master
            (

                machine_stage_id,

                template_name,

                description

            )
            VALUES
            (?, ?, ?)
            """,
            (

                machine_stage_id,

                template_name,

                description

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_all_templates():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM template_master

            WHERE active = 1

            ORDER BY template_name
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]