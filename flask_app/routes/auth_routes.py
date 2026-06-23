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

                client_ip = request.remote_addr
                workstation_name = socket.gethostname()

                session_id = UserSessionManager.login(
                    username=username,
                    role=user["role"],
                    client_ip=client_ip,
                    workstation_name=workstation_name
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
                    client_ip=client_ip
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
                client_ip=request.remote_addr,
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
                client_ip=request.remote_addr
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
                client_ip=request.remote_addr,
                record_id=username
            )

            flash("Password changed successfully.", "success")
            return redirect("/")

        return render_template("auth/my_password.html")
