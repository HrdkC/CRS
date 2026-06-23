from database.database import get_connection


class UserSessionManager:

    @staticmethod
    def login(
        username,
        client_ip,
        workstation_name,
        role=None
    ):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_sessions
            SET logout_time = CURRENT_TIMESTAMP,
                logout_reason = COALESCE(logout_reason, 'NEW_LOGIN')
            WHERE username = ?
              AND logout_time IS NULL
            """,
            (username,)
        )

        cursor.execute(
            """
            INSERT INTO user_sessions
            (
                username,
                role,
                client_ip,
                workstation_name,
                last_activity
            )
            VALUES
            (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                username,
                role,
                client_ip,
                workstation_name
            )
        )

        conn.commit()
        session_id = cursor.lastrowid
        conn.close()

        return session_id

    @staticmethod
    def logout(
        session_id,
        reason="USER_LOGOUT"
    ):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_sessions
            SET logout_time = CURRENT_TIMESTAMP,
                logout_reason = ?
            WHERE id = ?
              AND logout_time IS NULL
            """,
            (reason, session_id)
        )

        conn.commit()
        conn.close()

    @staticmethod
    def auto_logout(session_id):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_sessions
            SET logout_time = CURRENT_TIMESTAMP,
                logout_reason = 'AUTO_LOGOUT',
                auto_logged_out = 1
            WHERE id = ?
              AND logout_time IS NULL
            """,
            (session_id,)
        )

        conn.commit()
        conn.close()

    @staticmethod
    def force_logout(
        session_id,
        forced_by="SYSTEM"
    ):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_sessions
            SET logout_time = CURRENT_TIMESTAMP,
                logout_reason = ?
            WHERE id = ?
              AND logout_time IS NULL
            """,
            (f"FORCED_BY_{forced_by}", session_id)
        )

        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()

        return updated

    @staticmethod
    def touch(session_id):
        if not session_id:
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_sessions
            SET last_activity = CURRENT_TIMESTAMP
            WHERE id = ?
              AND logout_time IS NULL
            """,
            (session_id,)
        )

        conn.commit()
        conn.close()

    @staticmethod
    def get_active_sessions():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                role,
                client_ip,
                workstation_name,
                login_time,
                last_activity,
                ROUND((julianday('now') - julianday(login_time)) * 24 * 60, 1) AS active_minutes
            FROM user_sessions
            WHERE logout_time IS NULL
            ORDER BY last_activity DESC, login_time DESC
            """
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    @staticmethod
    def get_recent_sessions(limit=50):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                role,
                client_ip,
                workstation_name,
                login_time,
                last_activity,
                logout_time,
                logout_reason,
                auto_logged_out
            FROM user_sessions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
