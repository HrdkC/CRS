import time

from flask import (
    request,
    session,
    redirect,
    flash
)

from database.audit_manager import AuditManager
from database.system_settings_manager import SystemSettingsManager
from database.user_session_manager import UserSessionManager


SKIP_ENDPOINTS = {
    "login",
    "logout",
    "static",
    "my_password",
    "session_auto_expire"
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
                client_ip=request.remote_addr,
                reason=f"Idle timeout exceeded {timeout_minutes} minutes"
            )

            session.clear()
            flash("Session timed out due to inactivity. Please login again.", "warning")
            return redirect("/login")

        session["last_activity_epoch"] = now

        last_db_touch = int(session.get("last_db_touch_epoch", 0))
        if now - last_db_touch >= 60:
            UserSessionManager.touch(session.get("session_id"))
            session["last_db_touch_epoch"] = now

        if session.get("password_reset_required") == 1:
            return redirect("/my-password")

        return None
