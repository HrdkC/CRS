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

        recipe_id,

        include_inactive=False

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

                rpv.parameter_definition_id,

                pd.tag_index,

                pd.plc_array_index,

                pd.parameter_name,

                pd.unit,

                pd.min_value,

                pd.max_value,

                pd.default_value,

                COALESCE(pd.used, 1) AS used

            FROM
            recipe_parameter_values rpv

            INNER JOIN
            parameter_definitions pd

                ON pd.id =
                rpv.parameter_definition_id

            WHERE

                rpv.recipe_id = ?

                AND (
                    ? = 1
                    OR
                    COALESCE(pd.used, 1) = 1
                )

            ORDER BY
                pd.tag_index
            """,
            (
                recipe_id,
                1 if include_inactive else 0
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

        changed_by,

        change_reason="Recipe Parameter Update",

        user_role="EDITOR",

        change_source="DATABASE",

        client_ip=None,

        workstation_name=None

    ):

        from database.recipe_parameter_audit_manager import (
            RecipeParameterAuditManager
        )

        from database.audit_manager import (
            AuditManager
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

            return {

                "success": False,

                "changed": False,

                "message": "Recipe parameter value not found."

            }

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
            SELECT

                r.recipe_code,

                r.version,

                r.status,

                pd.parameter_name,

                pd.tag_index,

                pd.min_value,

                pd.max_value

            FROM recipes r

            INNER JOIN parameter_definitions pd

                ON pd.id = ?

            WHERE r.id = ?
            """,
            (
                parameter_definition_id,
                recipe_id
            )
        )

        audit_context = cursor.fetchone()

        if audit_context:

            min_value = audit_context[
                "min_value"
            ]

            max_value = audit_context[
                "max_value"
            ]

            if (
                min_value is not None
                and
                float(new_value) < float(min_value)
            ):

                conn.close()

                return {

                    "success": False,

                    "changed": False,

                    "message": f"Value below minimum limit ({min_value})."

                }

            if (
                max_value is not None
                and
                float(new_value) > float(max_value)
            ):

                conn.close()

                return {

                    "success": False,

                    "changed": False,

                    "message": f"Value above maximum limit ({max_value})."

                }

        if (
            old_value is not None
            and
            float(old_value) == float(new_value)
        ):

            conn.close()

            return {

                "success": True,

                "changed": False,

                "message": "No value change detected; audit entry was not created.",

                "old_value": old_value,

                "new_value": new_value

            }

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

        recipe_code = None

        recipe_version = None

        parameter_name = None

        tag_index = None

        if audit_context:

            recipe_code = audit_context[
                "recipe_code"
            ]

            recipe_version = audit_context[
                "version"
            ]

            parameter_name = audit_context[
                "parameter_name"
            ]

            tag_index = audit_context[
                "tag_index"
            ]

        parameter_audit_id = RecipeParameterAuditManager.log_change(

            recipe_id=recipe_id,

            recipe_parameter_value_id=value_id,

            parameter_definition_id=parameter_definition_id,

            old_value=old_value,

            new_value=new_value,

            changed_by=changed_by,

            recipe_code=recipe_code,

            recipe_version=recipe_version,

            parameter_name=parameter_name,

            tag_index=tag_index,

            change_source=change_source,

            change_reason=change_reason,

            user_role=user_role,

            client_ip=client_ip,

            workstation_name=workstation_name

        )

        if audit_context:

            AuditManager.log_event(

                username=changed_by,

                role=user_role,

                action="RECIPE_PARAMETER_CHANGED",

                change_source=change_source,

                recipe_code=recipe_code,

                recipe_version=recipe_version,

                record_id=value_id,

                parameter_name=parameter_name,

                old_value=str(
                    old_value
                ),

                new_value=str(
                    new_value
                ),

                reason=change_reason

            )

        return {

            "success": True,

            "changed": True,

            "message": "Recipe parameter updated and audited successfully.",

            "parameter_audit_id": parameter_audit_id,

            "recipe_id": recipe_id,

            "recipe_code": recipe_code,

            "recipe_version": recipe_version,

            "parameter_name": parameter_name,

            "old_value": old_value,

            "new_value": new_value,

            "change_source": change_source

        }
