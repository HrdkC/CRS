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
    def get_audit_history(
        limit=100,
        username=None,
        role=None,
        action=None,
        change_source=None,
        date_from=None,
        date_to=None,
        keyword=None
    ):
        conn = get_connection()
        cursor = conn.cursor()

        conditions = []
        params = []

        if username:
            conditions.append("LOWER(username) LIKE LOWER(?)")
            params.append(f"%{username.strip()}%")

        if role:
            conditions.append("UPPER(role) = UPPER(?)")
            params.append(role.strip())

        if action:
            conditions.append("UPPER(action) = UPPER(?)")
            params.append(action.strip())

        if change_source:
            conditions.append("UPPER(change_source) = UPPER(?)")
            params.append(change_source.strip())

        if date_from:
            # HTML date is local plant date. SQLite timestamp is UTC text, but
            # date filtering is intentionally broad and operator-friendly.
            conditions.append("DATE(timestamp) >= DATE(?)")
            params.append(date_from.strip())

        if date_to:
            conditions.append("DATE(timestamp) <= DATE(?)")
            params.append(date_to.strip())

        if keyword:
            keyword_value = f"%{keyword.strip()}%"
            conditions.append(
                "(" 
                "LOWER(COALESCE(username, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(role, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(action, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(change_source, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(reason, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(recipe_code, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(parameter_name, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(plc_name, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(old_value, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(new_value, '')) LIKE LOWER(?)"
                ")"
            )
            params.extend([keyword_value] * 10)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        try:
            safe_limit = int(limit)
        except (TypeError, ValueError):
            safe_limit = 100

        safe_limit = max(10, min(safe_limit, 5000))

        cursor.execute(
            f"""
            SELECT *
            FROM audit_log
            {where_clause}
            ORDER BY id DESC
            LIMIT ?
            """,
            params + [safe_limit]
        )

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_filter_options():
        conn = get_connection()
        cursor = conn.cursor()

        def fetch_distinct(column_name):
            cursor.execute(
                f"""
                SELECT DISTINCT {column_name}
                FROM audit_log
                WHERE {column_name} IS NOT NULL
                AND TRIM({column_name}) <> ''
                ORDER BY {column_name}
                """
            )
            return [row[0] for row in cursor.fetchall()]

        options = {
            "roles": fetch_distinct("role"),
            "actions": fetch_distinct("action"),
            "sources": fetch_distinct("change_source")
        }

        conn.close()
        return options

    @staticmethod
    def get_parameter_history(recipe_code, parameter_name):
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
            (recipe_code, parameter_name)
        )

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
