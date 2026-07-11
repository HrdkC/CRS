from flask import (
    render_template,
    request,
    redirect,
    session,
    flash
)

import os
import time

from database.user_manager import UserManager
from database.user_session_manager import UserSessionManager
from database.audit_manager import AuditManager

from helper.datetime_helper import utc_to_ist
from flask_app.security.login_throttle import (
    is_login_blocked,
    record_login_failure,
    record_login_success,
)
from flask_app.security.password_policy import validate_password_strength


def _client_metadata():
    """Return traceability metadata without exposing it on blocked login page."""
    trust_proxy_headers = os.getenv(
        "CRS_TRUST_PROXY_HEADERS",
        "0"
    ).strip().lower() in {"1", "true", "yes", "on"}
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = (
        forwarded_for.split(",")[0].strip()
        if trust_proxy_headers and forwarded_for
        else request.remote_addr
    )
    request_host = request.host
    user_agent = request.headers.get("User-Agent", "")
    workstation_name = (
        request.headers.get("X-Workstation-Name")
        or request.headers.get("X-Client-Workstation")
        or request.headers.get("X-Forwarded-Host")
        or request.headers.get("X-Real-IP")
        or client_ip
        or "UNKNOWN_CLIENT"
    )
    return {
        "client_ip": client_ip,
        "forwarded_for": forwarded_for,
        "request_host": request_host,
        "user_agent": user_agent,
        "workstation_name": workstation_name,
    }


def register_auth_routes(app):

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password")
            meta = _client_metadata()
            client_ip = meta["client_ip"]

            blocked, remaining_seconds = is_login_blocked(username, client_ip)
            if blocked:
                wait_minutes = max(1, int((remaining_seconds + 59) / 60))
                AuditManager.log_event(
                    username=username or "UNKNOWN",
                    role="UNKNOWN",
                    action="LOGIN_RATE_LIMIT_BLOCKED",
                    change_source="AUTH_RATE_LIMIT",
                    client_ip=meta["client_ip"],
                    user_agent=meta["user_agent"],
                    forwarded_for=meta["forwarded_for"],
                    request_host=meta["request_host"],
                    workstation_name=meta["workstation_name"],
                    reason=f"Too many failed login attempts. Retry after {wait_minutes} minute(s)."
                )
                return render_template(
                    "auth/login.html",
                    error=(
                        "Too many failed login attempts. "
                        f"Please wait {wait_minutes} minute(s) before retrying."
                    )
                )

            if UserManager.verify_user(username, password):
                user = UserManager.get_user(username)
                canonical_username = user["username"]
                forwarded_for = meta["forwarded_for"]
                request_host = meta["request_host"]
                user_agent = meta["user_agent"]
                workstation_name = meta["workstation_name"]

                active_session = UserSessionManager.get_live_active_session_for_username(canonical_username)
                if active_session:
                    UserSessionManager.record_blocked_login_attempt(
                        username=canonical_username,
                        active_session=active_session,
                        attempted_client_ip=client_ip,
                        attempted_workstation_name=workstation_name,
                        attempted_user_agent=user_agent,
                        attempted_forwarded_for=forwarded_for,
                        attempted_request_host=request_host,
                        login_source="WEB_LOGIN_BLOCKED_ACTIVE_SESSION"
                    )

                    AuditManager.log_event(
                        username=canonical_username,
                        role=user["role"],
                        action="LOGIN_BLOCKED_ACTIVE_SESSION",
                        change_source="AUTH_ACTIVE_SESSION_GUARD",
                        workstation_name=workstation_name,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        forwarded_for=forwarded_for,
                        request_host=request_host,
                        record_id=active_session.get("id"),
                        reason=(
                            "Login blocked because the same username is already active "
                            f"on workstation {active_session.get('workstation_name') or '-'} "
                            f"IP {active_session.get('client_ip') or '-'}"
                        )
                    )

                    return render_template(
                        "auth/login.html",
                        error=(
                            "This username is already logged in. "
                            "Existing active user has priority. Please wait until that user logs out or the session expires."
                        )
                    )

                record_login_success(canonical_username, client_ip)
                UserManager.update_last_login(canonical_username)
                user = UserManager.get_user(canonical_username)
                last_login_ist = utc_to_ist(user["last_login"])

                session_id, replaced_count = UserSessionManager.login(
                    username=canonical_username,
                    role=user["role"],
                    client_ip=client_ip,
                    workstation_name=workstation_name,
                    user_agent=user_agent,
                    forwarded_for=forwarded_for,
                    request_host=request_host,
                    login_source="WEB_LOGIN"
                )

                now = int(time.time())

                session.clear()
                session["logged_in"] = True
                session["username"] = canonical_username
                session["role"] = user["role"]
                session["session_id"] = session_id
                session["last_login_ist"] = last_login_ist
                session["password_reset_required"] = user.get("password_reset_required", 0)
                session["last_activity_epoch"] = now
                session["last_db_touch_epoch"] = now

                AuditManager.log_event(
                    username=canonical_username,
                    role=user["role"],
                    action="LOGIN_SUCCESS",
                    change_source="AUTH",
                    workstation_name=workstation_name,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    forwarded_for=forwarded_for,
                    request_host=request_host,
                    reason="Single-session login established. Existing active sessions are never replaced automatically."
                )


                if session.get("password_reset_required") == 1:
                    flash("Please change your temporary password before continuing.", "warning")
                    return redirect("/my-password")

                return redirect("/")

            record_login_failure(username, client_ip)
            AuditManager.log_event(
                username=username,
                role="UNKNOWN",
                action="LOGIN_FAILED",
                change_source="AUTH",
                client_ip=meta["client_ip"],
                user_agent=meta["user_agent"],
                forwarded_for=meta["forwarded_for"],
                request_host=meta["request_host"],
                workstation_name=meta["workstation_name"],
                reason="Invalid username or password"
            )

            return render_template(
                "auth/login.html",
                error="Invalid Username Or Password"
            )

        return render_template("auth/login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        if session.get("session_id"):
            UserSessionManager.logout(
                session["session_id"],
                reason="USER_LOGOUT"
            )

        if session.get("logged_in"):
            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action="LOGOUT",
                change_source="AUTH",
                client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host
            )

        session.clear()
        return redirect("/login")

    @app.route("/my-password", methods=["GET", "POST"])
    def my_password():
        if not session.get("logged_in"):
            return redirect("/login")

        username = session.get("username")

        if request.method == "POST":
            current_password = request.form.get("current_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")

            if not UserManager.verify_user(username, current_password):
                return render_template(
                    "auth/my_password.html",
                    error="Current password is incorrect."
                )

            if new_password != confirm_password:
                return render_template(
                    "auth/my_password.html",
                    error="New passwords do not match."
                )

            password_ok, password_error = validate_password_strength(
                new_password,
                username=username
            )
            if not password_ok:
                return render_template(
                    "auth/my_password.html",
                    error=password_error
                )

            UserManager.change_password(
                username=username,
                new_password=new_password,
                require_reset=False
            )

            session["password_reset_required"] = 0

            AuditManager.log_event(
                username=username,
                role=session.get("role"),
                action="MY_PASSWORD_CHANGED",
                change_source="AUTH",
                client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                record_id=username,
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host
            )

            flash("Password changed successfully.", "success")
            return redirect("/")

        return render_template("auth/my_password.html")
