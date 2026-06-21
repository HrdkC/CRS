from database.database import (
    get_connection
)


class RecipeParameterValueManager:

    @staticmethod
    def create_values_from_template(

        recipe_id,

        machine_id,

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM parameter_definitions

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND used = 1

            ORDER BY tag_index
            """,
            (
                machine_id,
                stage_id
            )
        )

        parameters = cursor.fetchall()

        for parameter in parameters:

            cursor.execute(
                """
                INSERT INTO
                recipe_parameter_values
                (

                    recipe_id,

                    parameter_definition_id,

                    parameter_value,

                    is_modified

                )
                VALUES
                (?, ?, ?, 0)
                """,
                (
                    recipe_id,

                    parameter["id"],

                    parameter[
                        "default_value"
                    ]
                )
            )

        conn.commit()

        conn.close()

    @staticmethod
    def get_recipe_values(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                rpv.id,

                rpv.recipe_id,

                rpv.parameter_value,

                rpv.is_modified,

                pd.tag_index,

                pd.plc_array_index,

                pd.parameter_name,

                pd.unit,

                pd.min_value,

                pd.max_value,

                pd.default_value

            FROM
            recipe_parameter_values rpv

            INNER JOIN
            parameter_definitions pd

                ON pd.id =
                rpv.parameter_definition_id

            WHERE

                rpv.recipe_id = ?

            ORDER BY
                pd.tag_index
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
    def create_missing_values(

        machine_id,

        stage_id,

        parameter_definition_id,

        default_value

    ):

        from database.recipe_manager import (
            RecipeManager
        )

        conn = get_connection()

        cursor = conn.cursor()

        recipes = (

            RecipeManager
            .get_recipes_by_machine_stage(

                machine_id,

                stage_id

            )

        )

        for recipe in recipes:

            cursor.execute(
                """
                SELECT id

                FROM recipe_parameter_values

                WHERE

                    recipe_id = ?

                    AND parameter_definition_id = ?
                """,
                (
                    recipe["id"],
                    parameter_definition_id
                )
            )

            if cursor.fetchone():

                continue

            cursor.execute(
                """
                INSERT INTO
                recipe_parameter_values
                (

                    recipe_id,

                    parameter_definition_id,

                    parameter_value,

                    is_modified

                )
                VALUES
                (?, ?, ?, 0)
                """,
                (
                    recipe["id"],

                    parameter_definition_id,

                    default_value
                )
            )

        conn.commit()

        conn.close()
        
    @staticmethod
    def get_recipe_value_by_id(

        value_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                rpv.*,

                pd.parameter_name,

                pd.unit,

                pd.min_value,

                pd.max_value,

                pd.tag_index

            FROM
            recipe_parameter_values rpv

            INNER JOIN
            parameter_definitions pd

                ON pd.id =
                rpv.parameter_definition_id

            WHERE
                rpv.id = ?
            """,
            (
                value_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def update_recipe_value(

        value_id,

        new_value,

        changed_by

    ):

        from database.recipe_parameter_audit_manager import (
            RecipeParameterAuditManager
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_parameter_values

            WHERE id = ?
            """,
            (
                value_id,
            )
        )

        row = cursor.fetchone()

        if not row:

            conn.close()

            return

        old_value = row[
            "parameter_value"
        ]

        recipe_id = row[
            "recipe_id"
        ]

        parameter_definition_id = row[
            "parameter_definition_id"
        ]

        cursor.execute(
            """
            UPDATE
            recipe_parameter_values

            SET

                parameter_value = ?,

                is_modified = 1,

                updated_at =
                CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                new_value,
                value_id
            )
        )

        conn.commit()

        conn.close()

        RecipeParameterAuditManager.log_change(

            recipe_id=recipe_id,

            recipe_parameter_value_id=value_id,

            parameter_definition_id=parameter_definition_id,

            old_value=old_value,

            new_value=new_value,

            changed_by=changed_by

        )