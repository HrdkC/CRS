from database.database import get_connection
from database.system_settings_manager import SystemSettingsManager


class UserSessionManager:
    """Production-safe CRS user session helper.

    Final session policy:
    - Existing live active user has priority.
    - A second login for the same username is blocked if the first session is live.
    - Browser-close/stale sessions are closed automatically before login blocking.
    - New login screen never exposes active workstation/IP metadata.
    - Active user and ADMIN audit pages retain login-attempt metadata for traceability.
    """

    @staticmethod
    def _heartbeat_grace_seconds():
        try:
            return SystemSettingsManager.get_heartbeat_stale_grace_seconds()
        except Exception:
            return 75

    @staticmethod
    def _timeout_minutes():
        try:
            return SystemSettingsManager.get_session_timeout_minutes()
        except Exception:
            return 30

    @staticmethod
    def login(
        username,
        client_ip,
        workstation_name,
        role=None,
        user_agent=None,
        forwarded_for=None,
        request_host=None,
        login_source="WEB_LOGIN",
    ):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_sessions
            (
                username,
                role,
                client_ip,
                workstation_name,
                user_agent,
                forwarded_for,
                request_host,
                login_source,
                replaced_existing_sessions,
                last_activity,
                heartbeat_at
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                username,
                role,
                client_ip,
                workstation_name,
                user_agent,
                forwarded_for,
                request_host,
                login_source,
            )
        )

        conn.commit()
        session_id = cursor.lastrowid
        conn.close()

        return session_id, 0

    @staticmethod
    def logout(session_id, reason="USER_LOGOUT"):
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
    def auto_logout(session_id, reason="AUTO_LOGOUT"):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_sessions
            SET logout_time = CURRENT_TIMESTAMP,
                logout_reason = ?,
                auto_logged_out = 1
            WHERE id = ?
              AND logout_time IS NULL
            """,
            (reason, session_id)
        )

        conn.commit()
        conn.close()

    @staticmethod
    def force_logout(session_id, forced_by="SYSTEM"):
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
    def heartbeat(session_id, mark_user_activity=False):
        """Update liveness heartbeat. User activity is separate from liveness.

        heartbeat_at proves the browser tab is still alive.
        last_activity drives idle auto logout and should only update when the
        user interacted with the GUI or a real request was made.
        """
        if not session_id:
            return

        conn = get_connection()
        cursor = conn.cursor()

        if mark_user_activity:
            cursor.execute(
                """
                UPDATE user_sessions
                SET heartbeat_at = CURRENT_TIMESTAMP,
                    last_activity = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND logout_time IS NULL
                """,
                (session_id,)
            )
        else:
            cursor.execute(
                """
                UPDATE user_sessions
                SET heartbeat_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND logout_time IS NULL
                """,
                (session_id,)
            )

        conn.commit()
        conn.close()

    @staticmethod
    def touch(session_id):
        # Backward-compatible alias: a server request counts as user activity.
        UserSessionManager.heartbeat(session_id, mark_user_activity=True)

    @staticmethod
    def close_expired_and_stale_sessions(username=None, exclude_session_id=None):
        """Close stale active sessions permanently and safely.

        Permanent prevention for plant stoppage caused by browser close,
        workstation shutdown, network drop, or Flask restart leaving logout_time
        NULL. It never closes the currently requesting session when
        exclude_session_id is supplied.
        """
        timeout_minutes = UserSessionManager._timeout_minutes()
        heartbeat_grace_seconds = UserSessionManager._heartbeat_grace_seconds()

        reason = (
            f"STALE_OR_EXPIRED_SESSION_CLOSED "
            f"timeout={timeout_minutes}min heartbeat_grace={heartbeat_grace_seconds}s"
        )

        where_extra = ""
        params = [reason, int(timeout_minutes)]

        if username:
            where_extra += " AND username = ?"
            params.append(username)

        if exclude_session_id:
            where_extra += " AND id <> ?"
            params.append(exclude_session_id)

        params.extend([int(timeout_minutes), int(heartbeat_grace_seconds)])

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"""
            UPDATE user_sessions
            SET logout_time = CURRENT_TIMESTAMP,
                logout_reason = ?,
                auto_logged_out = CASE
                    WHEN (julianday('now') - julianday(COALESCE(last_activity, login_time))) * 24 * 60 > ?
                    THEN 1 ELSE COALESCE(auto_logged_out, 0)
                END
            WHERE logout_time IS NULL
              {where_extra}
              AND (
                    (julianday('now') - julianday(COALESCE(last_activity, login_time))) * 24 * 60 > ?
                 OR (julianday('now') - julianday(COALESCE(heartbeat_at, last_activity, login_time))) * 24 * 60 * 60 > ?
              )
            """,
            params
        )

        closed_count = cursor.rowcount
        conn.commit()
        conn.close()
        return closed_count

    @staticmethod
    def is_session_active(session_id, username=None):
        if not session_id:
            return False

        conn = get_connection()
        cursor = conn.cursor()
        if username:
            cursor.execute(
                """
                SELECT id
                FROM user_sessions
                WHERE id = ?
                  AND username = ?
                  AND logout_time IS NULL
                """,
                (session_id, username)
            )
        else:
            cursor.execute(
                """
                SELECT id
                FROM user_sessions
                WHERE id = ?
                  AND logout_time IS NULL
                """,
                (session_id,)
            )
        row = cursor.fetchone()
        conn.close()
        return row is not None

    @staticmethod
    def get_live_active_session_for_username(username):
        """Close stale sessions first, then return only a real live session."""
        if not username:
            return None

        UserSessionManager.close_expired_and_stale_sessions(username=username)

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
                user_agent,
                forwarded_for,
                request_host,
                login_source,
                login_time,
                last_activity,
                heartbeat_at,
                ROUND((julianday('now') - julianday(last_activity)) * 24 * 60, 1) AS idle_minutes,
                ROUND((julianday('now') - julianday(heartbeat_at)) * 24 * 60 * 60, 1) AS heartbeat_age_seconds
            FROM user_sessions
            WHERE username = ?
              AND logout_time IS NULL
            ORDER BY heartbeat_at DESC, last_activity DESC, login_time DESC
            LIMIT 1
            """,
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_active_session_for_username(username):
        # Backward-compatible public name.
        return UserSessionManager.get_live_active_session_for_username(username)

    @staticmethod
    def record_blocked_login_attempt(
        username,
        active_session,
        attempted_client_ip,
        attempted_workstation_name,
        attempted_user_agent=None,
        attempted_forwarded_for=None,
        attempted_request_host=None,
        login_source="WEB_LOGIN_BLOCKED_ACTIVE_SESSION"
    ):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_login_attempt_alerts
            (
                username,
                active_session_id,
                attempted_client_ip,
                attempted_workstation_name,
                attempted_user_agent,
                attempted_forwarded_for,
                attempted_request_host,
                active_client_ip,
                active_workstation_name,
                active_login_time,
                login_source,
                status
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNREAD')
            """,
            (
                username,
                active_session.get("id") if active_session else None,
                attempted_client_ip,
                attempted_workstation_name,
                attempted_user_agent,
                attempted_forwarded_for,
                attempted_request_host,
                active_session.get("client_ip") if active_session else None,
                active_session.get("workstation_name") if active_session else None,
                active_session.get("login_time") if active_session else None,
                login_source,
            )
        )

        conn.commit()
        alert_id = cursor.lastrowid
        conn.close()
        return alert_id

    @staticmethod
    def get_pending_login_attempt_alerts(username, limit=5):
        if not username:
            return []

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                username,
                active_session_id,
                attempted_at,
                attempted_client_ip,
                attempted_workstation_name,
                attempted_user_agent,
                attempted_forwarded_for,
                attempted_request_host,
                active_client_ip,
                active_workstation_name,
                active_login_time,
                login_source,
                status
            FROM user_login_attempt_alerts
            WHERE username = ?
              AND status = 'UNREAD'
            ORDER BY attempted_at DESC, id DESC
            LIMIT ?
            """,
            (username, int(limit or 5))
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def acknowledge_login_attempt_alert(alert_id, username):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE user_login_attempt_alerts
            SET status = 'ACKNOWLEDGED',
                acknowledged_at = CURRENT_TIMESTAMP,
                acknowledged_by = ?
            WHERE id = ?
              AND username = ?
              AND status = 'UNREAD'
            """,
            (username, alert_id, username)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    @staticmethod
    def get_active_sessions():
        UserSessionManager.close_expired_and_stale_sessions()

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
                user_agent,
                forwarded_for,
                request_host,
                login_source,
                replaced_existing_sessions,
                login_time,
                last_activity,
                heartbeat_at,
                ROUND((julianday('now') - julianday(login_time)) * 24 * 60, 1) AS active_minutes,
                ROUND((julianday('now') - julianday(last_activity)) * 24 * 60, 1) AS idle_minutes,
                ROUND((julianday('now') - julianday(heartbeat_at)) * 24 * 60 * 60, 1) AS heartbeat_age_seconds
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
                user_agent,
                forwarded_for,
                request_host,
                login_source,
                replaced_existing_sessions,
                login_time,
                last_activity,
                heartbeat_at,
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
