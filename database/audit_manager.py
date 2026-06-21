from database.database import get_connection


class AuditManager:

    @staticmethod
    def log_event(
        username,
        role,
        action,
        change_source="SYSTEM",
        workstation_name=None,
        client_ip=None,
        plc_name=None,
        recipe_code=None,
        recipe_version=None,
        record_id=None,
        parameter_name=None,
        old_value=None,
        new_value=None,
        reason=None
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO audit_log
            (
                username,
                role,

                workstation_name,
                client_ip,

                plc_name,

                recipe_code,
                recipe_version,

                record_id,

                parameter_name,

                old_value,
                new_value,

                action,

                change_source,

                reason
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                username,
                role,

                workstation_name,
                client_ip,

                plc_name,

                recipe_code,
                recipe_version,

                record_id,

                parameter_name,

                old_value,
                new_value,

                action,

                change_source,

                reason
            )
        )

        conn.commit()
        conn.close()

        return True

    @staticmethod
    def log_parameter_change(

        username,
        recipe_code,
        recipe_version,
        parameter_name,
        old_value,
        new_value,
        reason=None

    ):

        return AuditManager.log_event(

            username=username,

            role="EDITOR",

            action="PARAMETER_CHANGED",

            change_source="DATABASE",

            recipe_code=recipe_code,

            recipe_version=recipe_version,

            parameter_name=parameter_name,

            old_value=old_value,

            new_value=new_value,

            reason=reason

        )

    @staticmethod
    def get_audit_history(limit=100):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]
        
    @staticmethod
    def get_parameter_history(
        recipe_code,
        parameter_name
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM audit_log

            WHERE recipe_code = ?
            AND parameter_name = ?

            ORDER BY id DESC
            """,
            (
                recipe_code,
                parameter_name
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]