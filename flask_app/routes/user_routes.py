from flask import (
    request,
    render_template,
    session,
    redirect,
    flash
)

from helper.datetime_helper import utc_to_ist

from database.user_manager import UserManager
from database.audit_manager import AuditManager
from database.user_session_manager import UserSessionManager

from flask_app.security.role_guard import (
    role_options,
    role_label,
    is_protected_super_user
)
from flask_app.security.password_policy import validate_password_strength


def _admin_required():
    return session.get("role") == "ADMIN"


def _protected_super_user_message(username):
    if is_protected_super_user(username):
        return "Primary/backup super user account is protected from this UI action."
    return None


def register_user_routes(app):

    @app.route("/users")
    def users():
        if not _admin_required():
            return redirect("/")

        users = UserManager.list_users()
        role_counts = UserManager.role_summary()

        for user in users:
            user["created_at_ist"] = utc_to_ist(user.get("created_at"))
            user["last_login_ist"] = utc_to_ist(user.get("last_login"))
            user["password_changed_at_ist"] = utc_to_ist(user.get("password_changed_at"))
            user["disabled_at_ist"] = utc_to_ist(user.get("disabled_at"))
            user["role_label"] = role_label(user.get("role"))
            user["is_protected_super_user"] = is_protected_super_user(user.get("username"))

        return render_template(
            "users/users.html",
            users=users,
            role_options=role_options(),
            role_counts=role_counts
        )

    @app.route("/users/create", methods=["GET", "POST"])
    def create_user():
        if not _admin_required():
            return redirect("/")

        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            confirm_password = request.form.get("confirm_password")
            role = request.form.get("role")
            remarks = request.form.get("remarks")
            password_reset_required = 1 if request.form.get("password_reset_required") else 0

            if password != confirm_password:
                return render_template(
                    "users/create_user.html",
                    role_options=role_options(),
                    error="Passwords do not match."
                )

            password_ok, password_error = validate_password_strength(
                password,
                username=username
            )
            if not password_ok:
                return render_template(
                    "users/create_user.html",
                    role_options=role_options(),
                    error=password_error
                )

            created = UserManager.create_user(
                username=username,
                password=password,
                role=role,
                created_by=session["username"],
                password_reset_required=password_reset_required,
                remarks=remarks
            )

            if created:
                AuditManager.log_event(
                    username=session["username"],
                    role=session["role"],
                    action="USER_CREATED",
                    change_source="WEB",
                    record_id=username,
                    new_value=role,
                    reason=remarks
                )

                flash(f"User created: {username}", "success")
                return redirect("/users")

            return render_template(
                "users/create_user.html",
                role_options=role_options(),
                error="User create failed. Check duplicate username or role."
            )

        return render_template(
            "users/create_user.html",
            role_options=role_options()
        )

    @app.route("/users/disable/<username>", methods=["POST"])
    def disable_user(username):
        if not _admin_required():
            return redirect("/")

        if username == session["username"]:
            flash("You cannot disable your own active account.", "warning")
            return redirect("/users")

        protected_message = _protected_super_user_message(username)
        if protected_message:
            flash(protected_message, "warning")
            return redirect("/users")

        if UserManager.is_last_active_admin(username):
            flash("Cannot disable the last active ADMIN account.", "warning")
            return redirect("/users")

        UserManager.disable_user(
            username=username,
            disabled_by=session["username"]
        )

        AuditManager.log_event(
            username=session["username"],
            role=session["role"],
            action="USER_DISABLED",
            change_source="WEB",
            record_id=username
        )

        flash(f"User disabled: {username}", "success")
        return redirect("/users")

    @app.route("/users/enable/<username>", methods=["POST"])
    def enable_user(username):
        if not _admin_required():
            return redirect("/")

        UserManager.enable_user(username)

        AuditManager.log_event(
            username=session["username"],
            role=session["role"],
            action="USER_ENABLED",
            change_source="WEB",
            record_id=username
        )

        flash(f"User enabled: {username}", "success")
        return redirect("/users")

    @app.route("/users/update_role/<username>", methods=["POST"])
    def update_user_role(username):
        if not _admin_required():
            return redirect("/")

        protected_message = _protected_super_user_message(username)
        if protected_message:
            flash(protected_message, "warning")
            return redirect("/users")

        new_role = request.form.get("role")
        user = UserManager.get_user(username)

        if not user:
            flash("User not found.", "warning")
            return redirect("/users")

        old_role = user.get("role")

        if old_role == "ADMIN" and new_role != "ADMIN" and UserManager.is_last_active_admin(username):
            flash("Cannot demote the last active ADMIN account.", "warning")
            return redirect("/users")

        updated = UserManager.update_role(
            username=username,
            role=new_role,
            updated_by=session["username"]
        )

        if updated:
            AuditManager.log_event(
                username=session["username"],
                role=session["role"],
                action="USER_ROLE_UPDATED",
                change_source="WEB",
                record_id=username,
                old_value=old_role,
                new_value=new_role
            )
            flash(f"Role updated for {username}: {new_role}", "success")
        else:
            flash("Role update failed.", "warning")

        return redirect("/users")

    @app.route("/users/change_password/<username>", methods=["GET", "POST"])
    def change_password(username):
        if not _admin_required():
            return redirect("/")

        if request.method == "POST":
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")
            require_reset = 1 if request.form.get("require_reset") else 0

            if new_password != confirm_password:
                return render_template(
                    "users/change_password.html",
                    username=username,
                    error="Passwords Do Not Match"
                )

            password_ok, password_error = validate_password_strength(
                new_password,
                username=username
            )
            if not password_ok:
                return render_template(
                    "users/change_password.html",
                    username=username,
                    error=password_error
                )

            UserManager.change_password(
                username=username,
                new_password=new_password,
                require_reset=require_reset
            )

            AuditManager.log_event(
                username=session["username"],
                role=session["role"],
                action="PASSWORD_RESET_BY_ADMIN",
                change_source="WEB",
                record_id=username,
                reason="Require reset on next login" if require_reset else None
            )

            flash(f"Password reset for {username}", "success")
            return redirect("/users")

        return render_template(
            "users/change_password.html",
            username=username
        )

    @app.route("/users/require_password_reset/<username>", methods=["POST"])
    def require_password_reset(username):
        if not _admin_required():
            return redirect("/")

        UserManager.mark_password_reset_required(username, True)

        AuditManager.log_event(
            username=session["username"],
            role=session["role"],
            action="PASSWORD_RESET_REQUIRED",
            change_source="WEB",
            record_id=username
        )

        flash(f"Password reset required on next login for {username}", "success")
        return redirect("/users")
