import time

from flask import (
    jsonify,
    render_template,
    request,
    session,
    redirect,
    flash
)

from database.audit_manager import AuditManager
from database.system_settings_manager import SystemSettingsManager
from database.user_session_manager import UserSessionManager

from helper.datetime_helper import utc_to_ist


def _admin_required():
    return session.get("role") == "ADMIN"


def register_session_routes(app):

    @app.route("/active-sessions")
    def active_sessions():
        if not _admin_required():
            return redirect("/")

        sessions = UserSessionManager.get_active_sessions()
        timeout_record = SystemSettingsManager.get_setting_record(
            SystemSettingsManager.SESSION_TIMEOUT_KEY
        )
        timeout_minutes = SystemSettingsManager.get_session_timeout_minutes()

        for row in sessions:
            row["login_time_ist"] = utc_to_ist(row.get("login_time"))
            row["last_activity_ist"] = utc_to_ist(row.get("last_activity"))

        return render_template(
            "sessions/active_sessions.html",
            sessions=sessions,
            timeout_minutes=timeout_minutes,
            timeout_record=timeout_record,
            min_timeout=SystemSettingsManager.MIN_SESSION_TIMEOUT_MINUTES,
            max_timeout=SystemSettingsManager.MAX_SESSION_TIMEOUT_MINUTES
        )

    @app.route("/active-sessions/auto-logout-config", methods=["POST"])
    def update_auto_logout_config():
        if not _admin_required():
            return redirect("/")

        old_timeout = SystemSettingsManager.get_session_timeout_minutes()
        raw_timeout = request.form.get("timeout_minutes")

        try:
            new_timeout = SystemSettingsManager.set_session_timeout_minutes(
                timeout_minutes=raw_timeout,
                updated_by=session.get("username", "ADMIN")
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect("/active-sessions")

        session["session_timeout_minutes"] = new_timeout
        session["session_timeout_seconds"] = new_timeout * 60
        session["last_activity_epoch"] = int(time.time())

        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="SESSION_TIMEOUT_UPDATED",
            change_source="WEB_ADMIN_SETTINGS",
            old_value=old_timeout,
            new_value=new_timeout,
            client_ip=request.remote_addr,
            reason=f"Auto logout timeout changed from {old_timeout} to {new_timeout} minutes"
        )

        flash(f"Auto logout timeout updated to {new_timeout} minute(s).", "success")
        return redirect("/active-sessions")

    @app.route("/active-sessions/logout/<int:session_id>", methods=["POST"])
    def force_logout_session(session_id):
        if not _admin_required():
            return redirect("/")

        if session_id == session.get("session_id"):
            flash("You cannot force logout your own active session.", "warning")
            return redirect("/active-sessions")

        updated = UserSessionManager.force_logout(
            session_id=session_id,
            forced_by=session.get("username", "ADMIN")
        )

        if updated:
            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action="SESSION_FORCE_LOGOUT",
                change_source="WEB",
                record_id=session_id
            )
            flash("Session was force logged out.", "success")
        else:
            flash("Session was already closed or not found.", "warning")

        return redirect("/active-sessions")

    @app.route("/session-heartbeat", methods=["POST"])
    def session_heartbeat():
        if not session.get("logged_in"):
            return jsonify({"ok": False, "redirect": "/login"}), 401

        now = int(time.time())
        timeout_minutes = SystemSettingsManager.get_session_timeout_minutes()
        timeout_seconds = timeout_minutes * 60

        session["last_activity_epoch"] = now
        session["last_db_touch_epoch"] = now
        session["session_timeout_minutes"] = timeout_minutes
        session["session_timeout_seconds"] = timeout_seconds

        UserSessionManager.touch(session.get("session_id"))

        return jsonify(
            {
                "ok": True,
                "timeout_minutes": timeout_minutes,
                "timeout_seconds": timeout_seconds,
                "last_activity_epoch": now,
                "remaining_seconds": timeout_seconds
            }
        )

    @app.route("/session-auto-expire", methods=["POST"])
    def session_auto_expire():
        if not session.get("logged_in"):
            return jsonify({"ok": True, "redirect": "/login"})

        username = session.get("username")
        role = session.get("role")
        session_id = session.get("session_id")
        timeout_minutes = SystemSettingsManager.get_session_timeout_minutes()

        if session_id:
            UserSessionManager.auto_logout(session_id)

        AuditManager.log_event(
            username=username,
            role=role,
            action="AUTO_LOGOUT",
            change_source="CLIENT_COUNTDOWN_TIMER",
            client_ip=request.remote_addr,
            reason=f"GUI countdown expired after {timeout_minutes} minute(s)"
        )

        session.clear()

        return jsonify(
            {
                "ok": True,
                "redirect": "/login",
                "message": "Session timed out due to inactivity. Please login again."
            }
        )
