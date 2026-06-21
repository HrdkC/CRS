from database.database import (
    get_connection
)


class RecipeStatusHistoryManager:

    @staticmethod
    def add_history(

        recipe_id,

        recipe_code,

        old_status,

        new_status,

        changed_by,

        remarks=""

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO
            recipe_status_history
            (

                recipe_id,

                recipe_code,

                old_status,

                new_status,

                changed_by,

                remarks

            )
            VALUES
            (?, ?, ?, ?, ?, ?)
            """,
            (

                recipe_id,

                recipe_code,

                old_status,

                new_status,

                changed_by,

                remarks

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_history(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_status_history

            WHERE recipe_id = ?

            ORDER BY
                changed_at DESC,
                id DESC
            """,
            (
                recipe_id,
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [

            dict(row)

            for row in rows

        ]