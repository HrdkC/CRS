import uuid

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
        workstation_name=None,
    ):
        """Atomically update one recipe value and both audit records."""
        from database.recipe_parameter_audit_manager import RecipeParameterAuditManager
        from database.audit_manager import AuditManager

        reason = (change_reason or "").strip()
        if not reason:
            return {
                "success": False,
                "changed": False,
                "message": "A change reason is required.",
            }

        correlation_id = uuid.uuid4().hex
        try:
            numeric_new_value = float(new_value)
        except (TypeError, ValueError):
            return {
                "success": False,
                "changed": False,
                "message": "Parameter value must be numeric.",
            }

        try:
            with transaction(immediate=True) as conn:
                cursor = conn.cursor()
                row = cursor.execute(
                    """
                    SELECT
                        rpv.id, rpv.recipe_id, rpv.parameter_definition_id,
                        rpv.parameter_value, rpv.updated_at,
                        r.recipe_code, r.version, r.status, r.machine_id, r.stage_id,
                        pd.parameter_name, pd.tag_index, pd.min_value, pd.max_value,
                        CASE
                            WHEN r.status='RELEASED' AND r.id=(
                                SELECT x.id FROM recipes x
                                WHERE x.machine_id=r.machine_id
                                  AND x.stage_id=r.stage_id
                                  AND UPPER(x.recipe_code)=UPPER(r.recipe_code)
                                  AND x.status='RELEASED'
                                ORDER BY x.version DESC, x.id DESC LIMIT 1
                            ) THEN 1 ELSE 0
                        END AS is_current_released
                    FROM recipe_parameter_values rpv
                    JOIN recipes r ON r.id=rpv.recipe_id
                    JOIN parameter_definitions pd ON pd.id=rpv.parameter_definition_id
                    WHERE rpv.id=?
                    """,
                    (int(value_id),),
                ).fetchone()

                if not row:
                    return {
                        "success": False,
                        "changed": False,
                        "message": "Recipe parameter value not found.",
                    }

                if row["status"] == "RELEASED" and int(row["is_current_released"] or 0) != 1:
                    return {
                        "success": False,
                        "changed": False,
                        "message": "Historical released recipe values are read-only.",
                    }

                min_value = row["min_value"]
                max_value = row["max_value"]
                if min_value is not None and numeric_new_value < float(min_value):
                    return {
                        "success": False,
                        "changed": False,
                        "message": f"Value below minimum limit ({min_value}).",
                    }
                if max_value is not None and numeric_new_value > float(max_value):
                    return {
                        "success": False,
                        "changed": False,
                        "message": f"Value above maximum limit ({max_value}).",
                    }

                old_value = row["parameter_value"]
                if old_value is not None and float(old_value) == numeric_new_value:
                    return {
                        "success": True,
                        "changed": False,
                        "message": "No value change detected; audit entry was not created.",
                        "old_value": old_value,
                        "new_value": numeric_new_value,
                    }

                cursor.execute(
                    """
                    UPDATE recipe_parameter_values
                    SET parameter_value=?, is_modified=1, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (numeric_new_value, int(value_id)),
                )

                parameter_audit_id = RecipeParameterAuditManager.log_change(
                    recipe_id=row["recipe_id"],
                    recipe_parameter_value_id=int(value_id),
                    parameter_definition_id=row["parameter_definition_id"],
                    old_value=old_value,
                    new_value=numeric_new_value,
                    changed_by=changed_by,
                    recipe_code=row["recipe_code"],
                    recipe_version=row["version"],
                    parameter_name=row["parameter_name"],
                    tag_index=row["tag_index"],
                    change_source=change_source,
                    change_reason=reason,
                    user_role=user_role,
                    client_ip=client_ip,
                    workstation_name=workstation_name,
                    correlation_id=correlation_id,
                    _connection=conn,
                )
                AuditManager.log_event(
                    username=changed_by,
                    role=user_role,
                    action="RECIPE_PARAMETER_CHANGED",
                    change_source=change_source,
                    recipe_code=row["recipe_code"],
                    recipe_version=row["version"],
                    record_id=int(value_id),
                    parameter_name=row["parameter_name"],
                    old_value=str(old_value),
                    new_value=str(numeric_new_value),
                    reason=reason,
                    workstation_name=workstation_name,
                    client_ip=client_ip,
                    correlation_id=correlation_id,
                    _connection=conn,
                )

                return {
                    "success": True,
                    "changed": True,
                    "message": "Recipe parameter updated and audited successfully.",
                    "parameter_audit_id": parameter_audit_id,
                    "correlation_id": correlation_id,
                    "recipe_id": row["recipe_id"],
                    "recipe_code": row["recipe_code"],
                    "recipe_version": row["version"],
                    "parameter_name": row["parameter_name"],
                    "old_value": old_value,
                    "new_value": numeric_new_value,
                }
        except Exception as exc:
            return {
                "success": False,
                "changed": False,
                "message": "Recipe parameter update failed and was rolled back.",
                "error_type": type(exc).__name__,
                "correlation_id": correlation_id,
            }
