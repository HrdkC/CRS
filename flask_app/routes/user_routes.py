from flask import (
    request
)

from helper.datetime_helper import (
    utc_to_ist
)

from flask import (

    render_template,

    session,

    redirect

)

from database.user_manager import (
    UserManager
)

from database.audit_manager import (
    AuditManager
)

from flask_app.security.role_guard import (
    role_options
)

def register_user_routes(

    app

):

    @app.route("/users")
    def users():

        if session.get("role") != "ADMIN":

            return redirect("/")

        users = UserManager.list_users()

        for user in users:

            user["created_at_ist"] = utc_to_ist(
                user["created_at"]
            )

            user["last_login_ist"] = utc_to_ist(
                user["last_login"]
            )

        return render_template(

            "users/users.html",

            users=users

        )

    @app.route("/users/create", methods=["GET", "POST"])
    def create_user():

        if session.get("role") != "ADMIN":

            return redirect("/")

        if request.method == "POST":

            username = request.form.get("username")

            password = request.form.get("password")

            role = request.form.get("role")

            created = UserManager.create_user(

                username=username,

                password=password,

                role=role,

                created_by=session["username"]

            )

            if created:

                AuditManager.log_event(

                    username=session["username"],

                    role=session["role"],

                    action="USER_CREATED",

                    change_source="WEB",

                    record_id=username,

                    new_value=role

                )

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
    
    @app.route("/users/disable/<username>")
    def disable_user(username):

        if session.get(
            "role"
        ) != "ADMIN":

            return redirect("/")

        if username == session["username"]:

            return redirect("/users")

        UserManager.disable_user(username)

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="USER_DISABLED",

            change_source="WEB",

            record_id=username

        )

        return redirect("/users")
    
    @app.route("/users/enable/<username>")
    def enable_user(username):

        if session.get("role") != "ADMIN":

            return redirect("/")

        UserManager.enable_user(username)

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="USER_ENABLED",

            change_source="WEB",

            record_id=username

        )

        return redirect("/users")
    
    @app.route("/users/change_password/<username>", methods=["GET", "POST"])
    def change_password(username):

        if session.get("role") != "ADMIN":

            return redirect("/")

        if request.method == "POST":

            new_password = request.form.get(
                "new_password"
            )

            confirm_password = request.form.get(
                "confirm_password"
            )

            if new_password != confirm_password:

                return render_template(

                    "users/change_password.html",

                    username=username,

                    error="Passwords Do Not Match"

                )

            UserManager.change_password(username, new_password)

            AuditManager.log_event(

                username=session["username"],

                role=session["role"],

                action="PASSWORD_CHANGED",

                change_source="WEB",

                record_id=username

            )

            return redirect("/users")

        return render_template("users/change_password.html", username=username)
