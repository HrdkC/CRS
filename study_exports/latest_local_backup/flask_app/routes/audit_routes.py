from flask import (
    render_template,
    session,
    redirect
)

from database.audit_manager import (
    AuditManager
)

from helper.datetime_helper import (
    utc_to_ist
)


def register_audit_routes(app):

    @app.route("/audit-history")
    def audit_history():

        if not session.get("logged_in"):

            return redirect("/login")

        if session.get("role") != "ADMIN":

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