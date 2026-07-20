from database.database import (
    get_connection
)
from database.schema_guard import require_table


class RecipeParameterAuditManager:

    OPTIONAL_COLUMNS = {

        "recipe_code": "TEXT",

        "recipe_version": "INTEGER",

        "parameter_name": "TEXT",

        "tag_index": "INTEGER",

        "change_source": "TEXT DEFAULT 'DATABASE'",

        "change_reason": "TEXT",

        "user_role": "TEXT",

        "client_ip": "TEXT",

        "workstation_name": "TEXT"

    }

    @staticmethod
    def ensure_schema(cursor=None):
        required = {
            "recipe_id", "recipe_parameter_value_id",
            "parameter_definition_id", "old_value", "new_value",
            "changed_by", "recipe_code", "recipe_version",
            "parameter_name", "tag_index", "change_source",
            "change_reason", "user_role", "client_ip",
            "workstation_name", "correlation_id",
        }
        if cursor is None:
            return require_table("recipe_parameter_audit", required)
        exists = cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='recipe_parameter_audit'"
        ).fetchone()
        columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(recipe_parameter_audit)")
        } if exists else set()
        missing = sorted(required - columns)
        if missing:
            raise RuntimeError(
                "recipe_parameter_audit schema is not ready: " + ", ".join(missing)
            )
        return True

    @staticmethod
    def ensure_table(cursor=None):

        return RecipeParameterAuditManager.ensure_schema(cursor)

    @staticmethod
    def log_change(
        recipe_id,
        recipe_parameter_value_id,
        parameter_definition_id,
        old_value,
        new_value,
        changed_by,
        recipe_code=None,
        recipe_version=None,
        parameter_name=None,
        tag_index=None,
        change_source="DATABASE",
        change_reason=None,
        user_role=None,
        client_ip=None,
        workstation_name=None,
        correlation_id=None,
        _connection=None,
    ):
        owns_connection = _connection is None
        conn = _connection or get_connection()
        cursor = conn.cursor()
        RecipeParameterAuditManager.ensure_schema(cursor)
        cursor.execute(
            """
            INSERT INTO recipe_parameter_audit
            (
                recipe_id, recipe_parameter_value_id, parameter_definition_id,
                old_value, new_value, changed_by, recipe_code, recipe_version,
                parameter_name, tag_index, change_source, change_reason, user_role,
                client_ip, workstation_name, correlation_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipe_id, recipe_parameter_value_id, parameter_definition_id,
                old_value, new_value, changed_by, recipe_code, recipe_version,
                parameter_name, tag_index, change_source, change_reason, user_role,
                client_ip, workstation_name, correlation_id,
            ),
        )
        audit_id = cursor.lastrowid
        if owns_connection:
            conn.commit()
            conn.close()
        return audit_id

    @staticmethod
    def get_parameter_history(

        recipe_parameter_value_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        RecipeParameterAuditManager.ensure_schema(
            cursor
        )

        cursor.execute(
            """
            SELECT *

            FROM recipe_parameter_audit

            WHERE

                recipe_parameter_value_id = ?

            ORDER BY
                changed_at DESC,
                id DESC
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

        RecipeParameterAuditManager.ensure_schema(
            cursor
        )

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
            recipe_parameter_values rpv

            INNER JOIN
            parameter_definitions pd

                ON pd.id =
                rpv.parameter_definition_id

            WHERE
                rpv.recipe_id = ?

                AND
                COALESCE(pd.used, 1) = 1
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

                AND
                COALESCE(pd.used, 1) = 1
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

                changed_at,

                change_source,

                change_reason

            FROM
            recipe_parameter_audit

            WHERE
                recipe_id = ?

            ORDER BY
                changed_at DESC,
                id DESC

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

            summary[
                "last_change_source"
            ] = row[
                "change_source"
            ]

            summary[
                "last_change_reason"
            ] = row[
                "change_reason"
            ]

        else:

            summary[
                "last_changed_by"
            ] = "-"

            summary[
                "last_changed_at"
            ] = "-"

            summary[
                "last_change_source"
            ] = "-"

            summary[
                "last_change_reason"
            ] = "-"

        conn.close()

        return summary
