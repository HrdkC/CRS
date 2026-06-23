from flask import (
    render_template,
    session,
    redirect,
    flash
)

from database.user_session_manager import UserSessionManager
from database.audit_manager import AuditManager

from helper.datetime_helper import utc_to_ist


def register_session_routes(app):

    @app.route("/active-sessions")
    def active_sessions():
        if session.get("role") != "ADMIN":
            return redirect("/")

        sessions = UserSessionManager.get_active_sessions()

        for row in sessions:
            row["login_time_ist"] = utc_to_ist(row.get("login_time"))
            row["last_activity_ist"] = utc_to_ist(row.get("last_activity"))

        return render_template(
            "sessions/active_sessions.html",
            sessions=sessions
        )

    @app.route("/active-sessions/logout/<int:session_id>", methods=["POST"])
    def force_logout_session(session_id):
        if session.get("role") != "ADMIN":
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
