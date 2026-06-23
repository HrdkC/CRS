from flask import (
    render_template,
    session,
    redirect,
    flash
)

from database.audit_manager import (
    AuditManager
)

from helper.datetime_helper import (
    utc_to_ist
)

from flask_app.security.role_guard import (
    role_can
)


def register_audit_routes(app):

    @app.route("/audit-history")
    def audit_history():

        if not session.get("logged_in"):

            return redirect("/login")

        if not role_can(session.get("role"), "audit_view"):

            flash(
                "Your role cannot view audit history.",
                "error"
            )
            return redirect("/")

        history = AuditManager.get_audit_history(
            limit=500
        )

        for row in history:

            row["timestamp_ist"] = utc_to_ist(
                row["timestamp"]
            )

        return render_template(

            "audit/audit_history.html",

            history=history

        )
