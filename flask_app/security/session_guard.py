import time

from flask import (
    request,
    session,
    redirect,
    flash,
    g
)

from database.audit_manager import AuditManager
from database.system_settings_manager import SystemSettingsManager
from database.user_session_manager import UserSessionManager


BACKGROUND_ENDPOINTS = {
    "recipe_download_preparation_job_status",
    "recipe_download_preparation_live_status",
    "session_heartbeat",
}


SKIP_ENDPOINTS = {
    "login",
    "logout",
    "static",
    "my_password",
    "session_auto_expire",
    "session_heartbeat"
}


def _current_timeout_minutes():
    try:
        return SystemSettingsManager.get_session_timeout_minutes()
    except Exception:
        # Conservative fallback if DB is temporarily unavailable.
        return 30


def register_session_guard(app):

    @app.before_request
    def enforce_auto_logout_and_password_reset():
        endpoint = request.endpoint or ""

        if endpoint.startswith("static"):
            return None

        if not session.get("logged_in"):
            return None

        if endpoint in SKIP_ENDPOINTS:
            return None

        # Permanent stale-session prevention:
        # close other expired/stale sessions before guarding the current request.
        # Never close this current browser here; auto logout logic below handles it.
        try:
            UserSessionManager.close_expired_and_stale_sessions(
                exclude_session_id=session.get("session_id")
            )
        except Exception:
            pass

        authority = UserSessionManager.get_session_authority(
            session.get("session_id"),
            session.get("username")
        )
        if (
            not authority
            or int(authority.get("active") or 0) != 1
            or (authority.get("current_role") or "").upper()
               != (session.get("role") or "").upper()
        ):
            username = session.get("username")
            previous_role = session.get("role")
            UserSessionManager.revoke_user_sessions(
                username,
                reason="AUTHORITY_CHANGED_OR_USER_DISABLED"
            )
            AuditManager.log_event(
                username=username,
                role=previous_role,
                action="SESSION_REVOKED_AUTHORITY_CHANGED",
                change_source="SESSION_GUARD",
                client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
                reason="User disabled, role changed, or active session claim invalid."
            )
            session.clear()
            flash("Your access was changed by an administrator. Please login again.", "warning")
            return redirect("/login")

        session["password_reset_required"] = int(
            authority.get("password_reset_required") or 0
        )

        # Existing active user has priority. A second login attempt for the same
        # username is blocked at /login and logged as an alert. Here we only
        # reject the browser session if it was closed by logout, force logout,
        # or auto logout.
        if not UserSessionManager.is_session_active(
            session.get("session_id"),
            username=session.get("username")
        ):
            username = session.get("username")
            role = session.get("role")
            AuditManager.log_event(
                username=username,
                role=role,
                action="SESSION_CLOSED_BROWSER_REQUEST",
                change_source="SESSION_GUARD",
                client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
                reason="Browser used a session cookie for a closed CRS session."
            )
            session.clear()
            flash("Your CRS session is no longer active. Please login again.", "warning")
            return redirect("/login")

        now = int(time.time())
        last_activity = int(session.get("last_activity_epoch", now))
        timeout_minutes = _current_timeout_minutes()
        timeout_seconds = timeout_minutes * 60

        session["session_timeout_minutes"] = timeout_minutes
        session["session_timeout_seconds"] = timeout_seconds

        if now - last_activity > timeout_seconds:
            username = session.get("username")
            role = session.get("role")
            session_id = session.get("session_id")

            if session_id:
                UserSessionManager.auto_logout(session_id)

            AuditManager.log_event(
                username=username,
                role=role,
                action="AUTO_LOGOUT",
                change_source="SESSION_GUARD",
                client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
                reason=f"Idle timeout exceeded {timeout_minutes} minutes"
            )

            session.clear()
            flash("Session timed out due to inactivity. Please login again.", "warning")
            return redirect("/login")

        explicit_activity = request.headers.get("X-CRS-User-Activity", "").strip() == "1"
        background_request = endpoint in BACKGROUND_ENDPOINTS
        if explicit_activity or not background_request:
            session["last_activity_epoch"] = now

        last_db_touch = int(session.get("last_db_touch_epoch", 0))
        if now - last_db_touch >= 60:
            UserSessionManager.heartbeat(
                session.get("session_id"),
                mark_user_activity=(explicit_activity or not background_request)
            )
            session["last_db_touch_epoch"] = now

        if session.get("password_reset_required") == 1:
            return redirect("/my-password")

        try:
            g.login_attempt_alerts = UserSessionManager.get_pending_login_attempt_alerts(
                session.get("username"),
                limit=3
            )
        except Exception:
            g.login_attempt_alerts = []

        return None
