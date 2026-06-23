from flask import (
    render_template,
    session,
    redirect,
    flash,
    request
)

from database.audit_manager import AuditManager
from helper.datetime_helper import utc_to_ist
from flask_app.security.role_guard import role_can


def _clean_arg(name):
    value = request.args.get(name, "")
    return value.strip() if value else ""


def register_audit_routes(app):

    @app.route("/audit-history")
    def audit_history():
        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "audit_view"):
            flash("Your role cannot view audit history.", "danger")
            return redirect("/")

        filters = {
            "username": _clean_arg("username"),
            "role": _clean_arg("role"),
            "action": _clean_arg("action"),
            "change_source": _clean_arg("change_source"),
            "date_from": _clean_arg("date_from"),
            "date_to": _clean_arg("date_to"),
            "keyword": _clean_arg("keyword"),
            "limit": _clean_arg("limit") or "500"
        }

        try:
            limit = int(filters["limit"])
        except ValueError:
            limit = 500
            filters["limit"] = "500"

        history = AuditManager.get_audit_history(
            limit=limit,
            username=filters["username"] or None,
            role=filters["role"] or None,
            action=filters["action"] or None,
            change_source=filters["change_source"] or None,
            date_from=filters["date_from"] or None,
            date_to=filters["date_to"] or None,
            keyword=filters["keyword"] or None
        )

        for row in history:
            row["timestamp_ist"] = utc_to_ist(row["timestamp"])

        filter_options = AuditManager.get_filter_options()

        return render_template(
            "audit/audit_history.html",
            history=history,
            filters=filters,
            filter_options=filter_options
        )
