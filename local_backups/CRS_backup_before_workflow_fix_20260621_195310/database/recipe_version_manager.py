from database.database import (
    get_connection
)


class RecipeVersionManager:

    @staticmethod
    def create_version(

        recipe_id,

        version_comment,

        created_by

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                recipe_code

            FROM recipes

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        recipe = cursor.fetchone()

        if not recipe:

            conn.close()

            raise Exception(
                "Recipe Not Found"
            )

        recipe_code = recipe[
            "recipe_code"
        ]

        cursor.execute(
            """
            SELECT

                MAX(version)

            FROM recipe_versions

            WHERE recipe_id = ?
            """,
            (
                recipe_id,
            )
        )

        row = cursor.fetchone()

        current_version = row[0]

        if current_version is None:

            current_version = 0

        next_version = (

            current_version + 1

        )

        cursor.execute(
            """
            INSERT INTO
            recipe_versions
            (

                recipe_id,

                recipe_code,

                version,

                version_comment,

                created_by

            )
            VALUES
            (?, ?, ?, ?, ?)
            """,
            (
                recipe_id,

                recipe_code,

                next_version,

                version_comment,

                created_by
            )
        )

        recipe_version_id = (
            cursor.lastrowid
        )

        cursor.execute(
            """
            SELECT

                parameter_definition_id,

                parameter_value

            FROM
            recipe_parameter_values

            WHERE recipe_id = ?
            """,
            (
                recipe_id,
            )
        )

        values = cursor.fetchall()

        for value in values:

            cursor.execute(
                """
                INSERT INTO
                recipe_version_values
                (

                    recipe_version_id,

                    parameter_definition_id,

                    parameter_value

                )
                VALUES
                (?, ?, ?)
                """,
                (
                    recipe_version_id,

                    value[
                        "parameter_definition_id"
                    ],

                    value[
                        "parameter_value"
                    ]
                )
            )

        cursor.execute(
            """
            UPDATE recipes

            SET

                version = ?,

                updated_at =
                CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                next_version,
                recipe_id
            )
        )

        conn.commit()

        conn.close()

        return recipe_version_id

    @staticmethod
    def get_versions(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_versions

            WHERE recipe_id = ?

            ORDER BY
                version DESC
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

    @staticmethod
    def restore_version(

        recipe_version_id,

        restored_by

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_versions

            WHERE id = ?
            """,
            (
                recipe_version_id,
            )
        )

        version = cursor.fetchone()

        if not version:

            conn.close()

            raise Exception(
                "Version Not Found"
            )

        recipe_id = version[
            "recipe_id"
        ]

        cursor.execute(
            """
            SELECT *

            FROM recipe_version_values

            WHERE
                recipe_version_id = ?
            """,
            (
                recipe_version_id,
            )
        )

        snapshot_values = (
            cursor.fetchall()
        )

        for row in snapshot_values:

            cursor.execute(
                """
                UPDATE
                recipe_parameter_values

                SET

                    parameter_value = ?,

                    is_modified = 1,

                    updated_at =
                    CURRENT_TIMESTAMP

                WHERE

                    recipe_id = ?

                    AND

                    parameter_definition_id = ?
                """,
                (
                    row[
                        "parameter_value"
                    ],

                    recipe_id,

                    row[
                        "parameter_definition_id"
                    ]
                )
            )

        conn.commit()

        conn.close()