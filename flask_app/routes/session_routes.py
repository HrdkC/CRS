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
            flash("Only ADMIN super users can view active sessions.", "danger")
            return redirect("/")

        sessions = UserSessionManager.get_active_sessions()
        timeout_minutes = SystemSettingsManager.get_session_timeout_minutes()

        for row in sessions:
            row["login_time_ist"] = utc_to_ist(row.get("login_time"))
            row["last_activity_ist"] = utc_to_ist(row.get("last_activity"))

        return render_template(
            "sessions/active_sessions.html",
            sessions=sessions,
            timeout_minutes=timeout_minutes
        )

    @app.route("/auto-logout-settings", methods=["GET"])
    def auto_logout_settings():
        if not _admin_required():
            flash("Only ADMIN super users can configure auto logout time.", "danger")
            return redirect("/")

        timeout_record = SystemSettingsManager.get_setting_record(
            SystemSettingsManager.SESSION_TIMEOUT_KEY
        )
        timeout_minutes = SystemSettingsManager.get_session_timeout_minutes()
        heartbeat_grace_record = SystemSettingsManager.get_setting_record(
            SystemSettingsManager.HEARTBEAT_STALE_GRACE_KEY
        )
        heartbeat_grace_seconds = SystemSettingsManager.get_heartbeat_stale_grace_seconds()

        return render_template(
            "sessions/auto_logout_settings.html",
            timeout_minutes=timeout_minutes,
            timeout_record=timeout_record,
            heartbeat_grace_seconds=heartbeat_grace_seconds,
            heartbeat_grace_record=heartbeat_grace_record,
            min_timeout=SystemSettingsManager.MIN_SESSION_TIMEOUT_MINUTES,
            max_timeout=SystemSettingsManager.MAX_SESSION_TIMEOUT_MINUTES,
            min_heartbeat_grace=SystemSettingsManager.MIN_HEARTBEAT_STALE_GRACE_SECONDS,
            max_heartbeat_grace=SystemSettingsManager.MAX_HEARTBEAT_STALE_GRACE_SECONDS
        )

    @app.route("/auto-logout-settings/update", methods=["POST"])
    def update_auto_logout_settings():
        if not _admin_required():
            flash("Only ADMIN super users can update auto logout settings.", "danger")
            return redirect("/")

        old_timeout = SystemSettingsManager.get_session_timeout_minutes()
        old_grace_seconds = SystemSettingsManager.get_heartbeat_stale_grace_seconds()

        raw_timeout = request.form.get("timeout_minutes")
        raw_grace_seconds = request.form.get("heartbeat_grace_seconds")
        change_reason = (request.form.get("change_reason") or "").strip()

        try:
            new_timeout = SystemSettingsManager.set_session_timeout_minutes(
                timeout_minutes=raw_timeout,
                updated_by=session.get("username", "ADMIN")
            )
            new_grace_seconds = SystemSettingsManager.set_heartbeat_stale_grace_seconds(
                grace_seconds=raw_grace_seconds,
                updated_by=session.get("username", "ADMIN")
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect("/auto-logout-settings")

        session["session_timeout_minutes"] = new_timeout
        session["session_timeout_seconds"] = new_timeout * 60
        session["heartbeat_stale_grace_seconds"] = new_grace_seconds
        session["last_activity_epoch"] = int(time.time())

        old_value = f"idle_timeout={old_timeout} min; browser_close_grace={old_grace_seconds} sec"
        new_value = f"idle_timeout={new_timeout} min; browser_close_grace={new_grace_seconds} sec"

        reason = (
            change_reason
            or (
                "Auto logout settings changed from "
                f"{old_timeout} min / {old_grace_seconds} sec to "
                f"{new_timeout} min / {new_grace_seconds} sec"
            )
        )

        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="SESSION_TIMEOUT_UPDATED",
            change_source="WEB_AUTO_LOGOUT_SETTINGS",
            old_value=old_value,
            new_value=new_value,
            client_ip=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
            forwarded_for=request.headers.get("X-Forwarded-For"),
            request_host=request.host,
            reason=reason
        )

        flash(
            f"Auto logout settings saved: idle timeout {new_timeout} minute(s), browser-close grace {new_grace_seconds} second(s).",
            "success"
        )
        return redirect("/auto-logout-settings")

    # Backward-compatible endpoint. The setting has moved to a separate page.
    @app.route("/active-sessions/auto-logout-config", methods=["POST"])
    def update_auto_logout_config_legacy():
        return update_auto_logout_settings()

    @app.route("/active-sessions/logout/<int:session_id>", methods=["POST"])
    def force_logout_session(session_id):
        if not _admin_required():
            flash("Only ADMIN super users can force logout sessions.", "danger")
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
                change_source="WEB_ACTIVE_SESSIONS",
                record_id=session_id,
                client_ip=request.remote_addr,
                reason="ADMIN force logout from Active Sessions page"
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
        heartbeat_grace_seconds = SystemSettingsManager.get_heartbeat_stale_grace_seconds()
        last_activity_epoch = int(session.get("last_activity_epoch", now))

        if now - last_activity_epoch > timeout_seconds:
            username = session.get("username")
            role = session.get("role")
            session_id = session.get("session_id")

            if session_id:
                UserSessionManager.auto_logout(session_id)

            AuditManager.log_event(
                username=username,
                role=role,
                action="AUTO_LOGOUT",
                change_source="SESSION_HEARTBEAT",
                client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
                reason=f"Idle timeout exceeded {timeout_minutes} minute(s)"
            )

            session.clear()
            return jsonify(
                {
                    "ok": False,
                    "redirect": "/login",
                    "message": "Session timed out due to inactivity."
                }
            ), 401

        payload = request.get_json(silent=True) or {}
        user_activity = bool(payload.get("user_activity"))

        if user_activity:
            session["last_activity_epoch"] = now

        session["last_db_touch_epoch"] = now
        session["session_timeout_minutes"] = timeout_minutes
        session["session_timeout_seconds"] = timeout_seconds
        session["heartbeat_stale_grace_seconds"] = heartbeat_grace_seconds

        UserSessionManager.heartbeat(
            session.get("session_id"),
            mark_user_activity=user_activity
        )

        alerts = UserSessionManager.get_pending_login_attempt_alerts(
            session.get("username"),
            limit=3
        )

        return jsonify(
            {
                "ok": True,
                "timeout_minutes": timeout_minutes,
                "timeout_seconds": timeout_seconds,
                "heartbeat_stale_grace_seconds": heartbeat_grace_seconds,
                "last_activity_epoch": session.get("last_activity_epoch", last_activity_epoch),
                "remaining_seconds": timeout_seconds - (now - int(session.get("last_activity_epoch", last_activity_epoch))),
                "login_attempt_alerts": alerts
            }
        )


    @app.route("/login-attempt-alerts/<int:alert_id>/ack", methods=["POST"])
    def acknowledge_login_attempt_alert(alert_id):
        """Acknowledge same-username login attempt alert.

        This endpoint is intentionally POST-only because it changes alert state.
        It supports both normal form submit fallback and AJAX submit from main.js.
        """
        if not session.get("logged_in"):
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"ok": False, "redirect": "/login"}), 401
            flash("Please login again before acknowledging alerts.", "warning")
            return redirect("/login")

        username = session.get("username")
        updated = UserSessionManager.acknowledge_login_attempt_alert(
            alert_id=alert_id,
            username=username
        )

        if updated:
            AuditManager.log_event(
                username=username,
                role=session.get("role"),
                action="LOGIN_ATTEMPT_ALERT_ACKNOWLEDGED",
                change_source="SESSION_ALERT",
                record_id=alert_id,
                client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
                reason="Active user acknowledged same-username login attempt alert."
            )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": True, "acknowledged": bool(updated), "alert_id": alert_id})

        return redirect(request.referrer or "/")

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
