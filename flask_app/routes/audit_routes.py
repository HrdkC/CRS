from urllib.parse import urlencode

from flask import (
    render_template,
    session,
    redirect,
    flash,
    request,
    url_for
)

from database.audit_manager import AuditManager
from helper.datetime_helper import utc_to_ist
from flask_app.security.role_guard import role_can


def _clean_arg(name):
    value = request.args.get(name, "")
    return value.strip() if value else ""


def _int_arg(name, default=250):
    try:
        return int(_clean_arg(name) or default)
    except ValueError:
        return default


def _build_sort_links(current_filters, sortable_columns):
    links = {}
    current_sort = current_filters.get("sort_by") or "timestamp"
    current_dir = current_filters.get("sort_dir") or "desc"

    for key, label in sortable_columns.items():
        next_dir = "asc"
        if key == current_sort and current_dir == "asc":
            next_dir = "desc"

        args = {
            name: value
            for name, value in current_filters.items()
            if value not in (None, "")
        }
        args["sort_by"] = key
        args["sort_dir"] = next_dir

        links[key] = {
            "label": label,
            "url": url_for("audit_history") + "?" + urlencode(args),
            "active": key == current_sort,
            "direction": current_dir if key == current_sort else "",
            "symbol": "▲" if key == current_sort and current_dir == "asc" else "▼" if key == current_sort else "↕"
        }

    return links


def _has_active_filters(filters):
    for key in ["username", "role", "action", "change_source", "date_from", "date_to", "keyword"]:
        if filters.get(key):
            return True
    return False


def register_audit_routes(app):

    @app.route("/audit-history", endpoint="audit_history")
    def audit_history():
        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "audit_view"):
            flash("Your role cannot view audit history.", "danger")
            return redirect("/")

        raw_limit = _int_arg("limit", default=250)
        limit = max(25, min(raw_limit, 5000))

        sortable_columns = {
            "timestamp": "Date/Time",
            "username": "User",
            "role": "Role",
            "action": "Action",
            "recipe_code": "Recipe / Record",
            "parameter_name": "Parameter",
            "old_value": "Old → New",
            "change_source": "Source",
            "reason": "Reason",
        }

        sort_by = _clean_arg("sort_by") or "timestamp"
        if sort_by not in sortable_columns:
            sort_by = "timestamp"

        sort_dir = (_clean_arg("sort_dir") or "desc").lower()
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"

        filters = {
            "username": _clean_arg("username"),
            "role": _clean_arg("role"),
            "action": _clean_arg("action"),
            "change_source": _clean_arg("change_source"),
            "date_from": _clean_arg("date_from"),
            "date_to": _clean_arg("date_to"),
            "keyword": _clean_arg("keyword"),
            "limit": str(limit),
            "sort_by": sort_by,
            "sort_dir": sort_dir,
        }

        history = AuditManager.get_audit_history(
            limit=limit,
            username=filters["username"] or None,
            role=filters["role"] or None,
            action=filters["action"] or None,
            change_source=filters["change_source"] or None,
            date_from=filters["date_from"] or None,
            date_to=filters["date_to"] or None,
            keyword=filters["keyword"] or None,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        total_count = AuditManager.get_audit_count(
            username=filters["username"] or None,
            role=filters["role"] or None,
            action=filters["action"] or None,
            change_source=filters["change_source"] or None,
            date_from=filters["date_from"] or None,
            date_to=filters["date_to"] or None,
            keyword=filters["keyword"] or None,
        )

        for row in history:
            row["timestamp_ist"] = utc_to_ist(row["timestamp"])

        filter_options = AuditManager.get_filter_options()
        sort_links = _build_sort_links(filters, sortable_columns)

        return render_template(
            "audit/audit_history.html",
            history=history,
            filters=filters,
            filter_options=filter_options,
            total_count=total_count,
            limit=limit,
            sort_links=sort_links,
            has_active_filters=_has_active_filters(filters),
        )
