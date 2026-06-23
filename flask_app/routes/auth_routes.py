from flask import (
    render_template,
    request,
    redirect,
    session,
    flash
)

import socket
import time

from database.user_manager import UserManager
from database.user_session_manager import UserSessionManager
from database.audit_manager import AuditManager

from helper.datetime_helper import utc_to_ist


def register_auth_routes(app):

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

            if UserManager.verify_user(username, password):
                UserManager.update_last_login(username)

                user = UserManager.get_user(username)
                last_login_ist = utc_to_ist(user["last_login"])

                client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
                forwarded_for = request.headers.get("X-Forwarded-For")
                request_host = request.host
                user_agent = request.headers.get("User-Agent", "")

                try:
                    workstation_name = socket.gethostbyaddr(request.remote_addr)[0]
                except Exception:
                    workstation_name = socket.gethostname()

                active_session = UserSessionManager.get_live_active_session_for_username(username)
                if active_session:
                    UserSessionManager.record_blocked_login_attempt(
                        username=username,
                        active_session=active_session,
                        attempted_client_ip=client_ip,
                        attempted_workstation_name=workstation_name,
                        attempted_user_agent=user_agent,
                        attempted_forwarded_for=forwarded_for,
                        attempted_request_host=request_host,
                        login_source="WEB_LOGIN_BLOCKED_ACTIVE_SESSION"
                    )

                    AuditManager.log_event(
                        username=username,
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

                session_id, replaced_count = UserSessionManager.login(
                    username=username,
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
                session["username"] = username
                session["role"] = user["role"]
                session["session_id"] = session_id
                session["last_login_ist"] = last_login_ist
                session["password_reset_required"] = user.get("password_reset_required", 0)
                session["last_activity_epoch"] = now
                session["last_db_touch_epoch"] = now

                AuditManager.log_event(
                    username=username,
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

                print("LAST LOGIN IST =", session["last_login_ist"])

                if session.get("password_reset_required") == 1:
                    flash("Please change your temporary password before continuing.", "warning")
                    return redirect("/my-password")

                return redirect("/")

            AuditManager.log_event(
                username=username,
                role="UNKNOWN",
                action="LOGIN_FAILED",
                change_source="AUTH",
                client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
                reason="Invalid username or password"
            )

            return render_template(
                "auth/login.html",
                error="Invalid Username Or Password"
            )

        return render_template("auth/login.html")

    @app.route("/logout")
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

            if len(new_password or "") < 6:
                return render_template(
                    "auth/my_password.html",
                    error="Password must be at least 6 characters."
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
