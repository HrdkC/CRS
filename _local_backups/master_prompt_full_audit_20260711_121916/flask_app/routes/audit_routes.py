from urllib.parse import urlencode

from flask import (
    render_template,
    session,
    redirect,
    flash,
    request,
    url_for,
    send_file,
)

from database.audit_manager import AuditManager
from database.audit_archive_manager import AuditArchiveManager
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


def _request_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def _log_archive_event(action, new_value=None, old_value=None, reason=None):
    AuditManager.log_event(
        username=session.get("username"),
        role=session.get("role"),
        action=action,
        change_source="WEB_AUDIT_ARCHIVE",
        old_value=old_value,
        new_value=new_value,
        client_ip=_request_client_ip(),
        user_agent=request.headers.get("User-Agent", ""),
        forwarded_for=request.headers.get("X-Forwarded-For"),
        request_host=request.host,
        reason=reason,
    )


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

    @app.route("/audit-archive", methods=["GET", "POST"], endpoint="audit_archive")
    def audit_archive():
        if not session.get("logged_in"):
            return redirect("/login")

        if session.get("role") != "ADMIN":
            flash("Only ADMIN super users can access audit archive controls.", "danger")
            return redirect("/")

        AuditArchiveManager.ensure_tables()

        if request.method == "POST":
            action = request.form.get("archive_action", "")
            export_path = (request.form.get("export_path") or "").strip()
            reason = (request.form.get("reason") or "").strip()

            try:
                if action == "download_active_records":
                    rows = AuditManager.get_audit_history(limit=5000)
                    stream = AuditArchiveManager.build_excel_bytes(rows, export_type="ACTIVE_AUDIT_DOWNLOAD")
                    file_name = AuditArchiveManager._make_file_name("ACTIVE_AUDIT_DOWNLOAD")
                    _log_archive_event(
                        action="AUDIT_EXPORTED",
                        new_value=f"BROWSER_DOWNLOAD:{file_name}",
                        reason=reason or "Active audit downloaded as Excel through browser"
                    )
                    return send_file(
                        stream,
                        as_attachment=True,
                        download_name=file_name,
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                if action == "export_active_records":
                    rows = AuditManager.get_audit_history(limit=5000)
                    export_file = AuditArchiveManager.export_rows_to_excel(
                        rows=rows,
                        export_path=export_path,
                        exported_by=session.get("username"),
                        export_type="ACTIVE_AUDIT_EXPORT",
                        remarks=reason or "Active audit export"
                    )
                    _log_archive_event(
                        action="AUDIT_EXPORTED",
                        new_value=export_file,
                        reason=reason or "Active audit exported to approved server path"
                    )
                    flash(f"Audit export saved: {export_file}", "success")

                elif action == "download_archive_records":
                    rows = AuditArchiveManager.get_archive_history(limit=5000)
                    stream = AuditArchiveManager.build_excel_bytes(rows, export_type="ARCHIVED_AUDIT_DOWNLOAD")
                    file_name = AuditArchiveManager._make_file_name("ARCHIVED_AUDIT_DOWNLOAD")
                    _log_archive_event(
                        action="AUDIT_EXPORTED",
                        new_value=f"BROWSER_DOWNLOAD:{file_name}",
                        reason=reason or "Archived audit downloaded as Excel through browser"
                    )
                    return send_file(
                        stream,
                        as_attachment=True,
                        download_name=file_name,
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                elif action == "export_archive_records":
                    rows = AuditArchiveManager.get_archive_history(limit=5000)
                    export_file = AuditArchiveManager.export_rows_to_excel(
                        rows=rows,
                        export_path=export_path,
                        exported_by=session.get("username"),
                        export_type="ARCHIVED_AUDIT_EXPORT",
                        remarks=reason or "Archived audit export"
                    )
                    _log_archive_event(
                        action="AUDIT_EXPORTED",
                        new_value=export_file,
                        reason=reason or "Archived audit exported to approved server path"
                    )
                    flash(f"Archived audit export saved: {export_file}", "success")

                elif action == "archive_old_records":
                    retention_days = request.form.get("retention_days", "90")
                    export_excel = request.form.get("export_excel") == "1"
                    result = AuditArchiveManager.archive_older_than(
                        retention_days=retention_days,
                        archived_by=session.get("username"),
                        export_path=export_path if export_excel else None,
                        export_excel=export_excel,
                        remarks=reason
                    )
                    _log_archive_event(
                        action="AUDIT_ARCHIVE_CREATED",
                        old_value=str(retention_days),
                        new_value=str(result.get("archived_count")),
                        reason=reason or "Audit records archived by ADMIN"
                    )
                    export_note = f" Excel backup: {result.get('export_file')}" if result.get("export_file") else ""
                    flash(f"Archived {result.get('archived_count', 0)} audit record(s).{export_note}", "success")

                else:
                    flash("Select a valid archive/export action.", "warning")

            except Exception as exc:
                flash(f"Audit archive/export failed: {exc}", "danger")

            return redirect("/audit-archive")

        archived_history = AuditArchiveManager.get_archive_history(limit=250)
        archive_count = AuditArchiveManager.get_archive_count()
        recent_exports = AuditArchiveManager.get_recent_exports(limit=10)
        approved_export_locations = AuditArchiveManager.get_approved_export_locations()

        for row in archived_history:
            row["timestamp_ist"] = utc_to_ist(row.get("timestamp"))
            row["archived_at_ist"] = utc_to_ist(row.get("archived_at"))

        return render_template(
            "audit/audit_archive.html",
            archived_history=archived_history,
            archive_count=archive_count,
            recent_exports=recent_exports,
            approved_export_locations=approved_export_locations,
        )
