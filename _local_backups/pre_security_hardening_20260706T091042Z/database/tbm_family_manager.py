from database.database import get_connection


class TBMFamilyManager:

    @staticmethod
    def create_family(

        family_name,

        description="",

        created_by=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO tbm_families
            (

                family_name,

                description,

                created_by

            )
            VALUES
            (?, ?, ?)
            """,
            (

                family_name,

                description,

                created_by

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_all_families():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM tbm_families

            ORDER BY family_name
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_family_by_id(

        family_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM tbm_families

            WHERE id = ?
            """,
            (
                family_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def update_family(

        family_id,

        family_name,

        description

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_families

            SET

                family_name = ?,

                description = ?

            WHERE id = ?
            """,
            (

                family_name,

                description,

                family_id

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def disable_family(

        family_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_families

            SET active = 0

            WHERE id = ?
            """,
            (
                family_id,
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def enable_family(

        family_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_families

            SET active = 1

            WHERE id = ?
            """,
            (
                family_id,
            )
        )

        conn.commit()

        conn.close()