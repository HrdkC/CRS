from database.database import (
    get_connection
)


class RecipeParameterAuditManager:

    @staticmethod
    def log_change(

        recipe_id,

        recipe_parameter_value_id,

        parameter_definition_id,

        old_value,

        new_value,

        changed_by

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO
            recipe_parameter_audit
            (

                recipe_id,

                recipe_parameter_value_id,

                parameter_definition_id,

                old_value,

                new_value,

                changed_by

            )
            VALUES
            (?, ?, ?, ?, ?, ?)
            """,
            (
                recipe_id,

                recipe_parameter_value_id,

                parameter_definition_id,

                old_value,

                new_value,

                changed_by
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_parameter_history(

        recipe_parameter_value_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_parameter_audit

            WHERE

                recipe_parameter_value_id = ?

            ORDER BY
                changed_at DESC
            """,
            (
                recipe_parameter_value_id,
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_recipe_summary(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                COUNT(*) AS total_parameters,

                SUM(
                    CASE
                        WHEN is_modified = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS modified_parameters

            FROM
            recipe_parameter_values

            WHERE
                recipe_id = ?
            """,
            (
                recipe_id,
            )
        )

        summary = dict(
            cursor.fetchone()
        )

        cursor.execute(
            """
            SELECT

                MIN(pd.tag_index) AS min_tag,

                MAX(pd.tag_index) AS max_tag

            FROM
            recipe_parameter_values rpv

            INNER JOIN
            parameter_definitions pd

                ON pd.id =
                rpv.parameter_definition_id

            WHERE
                rpv.recipe_id = ?
            """,
            (
                recipe_id,
            )
        )

        tag_data = dict(
            cursor.fetchone()
        )

        summary.update(
            tag_data
        )

        cursor.execute(
            """
            SELECT

                changed_by,

                changed_at

            FROM
            recipe_parameter_audit

            WHERE
                recipe_id = ?

            ORDER BY
                changed_at DESC

            LIMIT 1
            """,
            (
                recipe_id,
            )
        )

        row = cursor.fetchone()

        if row:

            summary[
                "last_changed_by"
            ] = row[
                "changed_by"
            ]

            summary[
                "last_changed_at"
            ] = row[
                "changed_at"
            ]

        else:

            summary[
                "last_changed_by"
            ] = "-"

            summary[
                "last_changed_at"
            ] = "-"

        conn.close()

        return summary