from flask import (
    render_template,
    session,
    redirect
)

from database.user_session_manager import (
    UserSessionManager
)

from helper.datetime_helper import (
    utc_to_ist
)


def register_session_routes(app):

    @app.route("/active-sessions")
    def active_sessions():

        if session.get("role") != "ADMIN":

            return redirect("/")

        sessions = UserSessionManager.get_active_sessions()

        for row in sessions:

            row["login_time_ist"] = utc_to_ist(
                row["login_time"]
            )

        return render_template(

            "sessions/active_sessions.html",

            sessions=sessions

        )