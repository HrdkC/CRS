import json

from flask import flash, redirect, render_template, request, session

from database.audit_manager import AuditManager
from database.database_configuration_manager import DatabaseConfigurationManager


def _admin_required():
    return session.get("logged_in") and session.get("role") == "ADMIN"


def _request_metadata():
    return {
        "user_agent": request.headers.get("User-Agent", ""),
        "forwarded_for": request.headers.get("X-Forwarded-For"),
        "request_host": request.host,
    }


def _profile_summary(profile):
    if not profile or profile.get("profile_error"):
        return profile
    return {
        key: profile.get(key)
        for key in (
            "engine",
            "host",
            "port",
            "database",
            "username",
            "ssl_mode",
            "ssl_ca_path",
            "updated_by",
            "updated_at_utc",
            "last_tested_at_utc",
            "last_tested_server_version",
            "runtime_activation",
        )
    }


def _form_fields():
    fields = {
        "host": request.form.get("host"),
        "port": request.form.get("port"),
        "database": request.form.get("database"),
        "username": request.form.get("username"),
        "password": request.form.get("password"),
        "ssl_mode": request.form.get("ssl_mode"),
        "ssl_ca_path": request.form.get("ssl_ca_path"),
    }

    if not fields["password"]:
        saved = DatabaseConfigurationManager.load_profile(include_password=True)
        if saved and not saved.get("profile_error"):
            fields["password"] = saved.get("password")
    return fields


def _audit(action, old_value=None, new_value=None, reason=None):
    try:
        AuditManager.log_event(
            username=session.get("username", "ADMIN"),
            role=session.get("role", "ADMIN"),
            action=action,
            change_source="DATABASE_CONFIGURATION",
            old_value=(
                json.dumps(old_value, sort_keys=True)
                if isinstance(old_value, dict)
                else old_value
            ),
            new_value=(
                json.dumps(new_value, sort_keys=True)
                if isinstance(new_value, dict)
                else new_value
            ),
            reason=reason,
            **_request_metadata(),
        )
    except Exception:
        # A database connection setup page must remain available when audit
        # storage is unavailable. The UI still reports the primary operation.
        pass


def register_database_configuration_routes(app):
    @app.route("/administration/database", methods=["GET"])
    def database_configuration():
        if not _admin_required():
            flash("Only ADMIN super users can configure database connectivity.", "danger")
            return redirect("/")

        profile = DatabaseConfigurationManager.load_profile()
        return render_template(
            "configuration/database_configuration.html",
            profile=profile,
            runtime_status=DatabaseConfigurationManager.runtime_status(),
            test_result=None,
            form_values=profile or {},
        )

    @app.route("/administration/database/test", methods=["POST"])
    def database_configuration_test():
        if not _admin_required():
            flash("Only ADMIN super users can test database connectivity.", "danger")
            return redirect("/")

        fields = _form_fields()
        result = DatabaseConfigurationManager.test_connection(fields)
        summary = _profile_summary(result.get("fields") or {})
        _audit(
            "DATABASE_CONNECTION_TEST_SUCCESS"
            if result.get("ok")
            else "DATABASE_CONNECTION_TEST_FAILED",
            new_value=summary,
            reason="ADMIN initiated MySQL connectivity test",
        )
        return render_template(
            "configuration/database_configuration.html",
            profile=DatabaseConfigurationManager.load_profile(),
            runtime_status=DatabaseConfigurationManager.runtime_status(),
            test_result=result,
            form_values=result.get("fields") or fields,
        )

    @app.route("/administration/database/save", methods=["POST"])
    def database_configuration_save():
        if not _admin_required():
            flash("Only ADMIN super users can save database configuration.", "danger")
            return redirect("/")

        reason = str(request.form.get("change_reason") or "").strip()
        if not reason:
            flash("A change reason is required before saving database configuration.", "warning")
            return redirect("/administration/database")

        fields = _form_fields()
        old_profile = DatabaseConfigurationManager.load_profile()
        result = DatabaseConfigurationManager.test_connection(fields)
        if not result.get("ok"):
            _audit(
                "DATABASE_PROFILE_SAVE_BLOCKED",
                old_value=_profile_summary(old_profile),
                new_value=_profile_summary(result.get("fields") or {}),
                reason=reason,
            )
            return render_template(
                "configuration/database_configuration.html",
                profile=old_profile,
                runtime_status=DatabaseConfigurationManager.runtime_status(),
                test_result=result,
                form_values=result.get("fields") or fields,
            )

        saved_profile = DatabaseConfigurationManager.save_profile(
            result["fields"],
            updated_by=session.get("username", "ADMIN"),
            test_result=result,
        )
        _audit(
            "DATABASE_PROFILE_SAVED",
            old_value=_profile_summary(old_profile),
            new_value=_profile_summary(saved_profile),
            reason=reason,
        )
        flash(
            "MySQL connection passed and the profile was saved with Windows DPAPI protection. "
            "Restart is not requested because MySQL runtime activation is still migration-blocked.",
            "success",
        )
        return redirect("/administration/database")

    @app.route("/administration/database/test-saved", methods=["POST"])
    def database_configuration_test_saved():
        if not _admin_required():
            flash("Only ADMIN super users can test database connectivity.", "danger")
            return redirect("/")

        result = DatabaseConfigurationManager.test_saved_profile()
        _audit(
            "SAVED_DATABASE_CONNECTION_TEST_SUCCESS"
            if result.get("ok")
            else "SAVED_DATABASE_CONNECTION_TEST_FAILED",
            new_value=_profile_summary(DatabaseConfigurationManager.load_profile()),
            reason="ADMIN tested the saved DPAPI-protected MySQL profile",
        )
        return render_template(
            "configuration/database_configuration.html",
            profile=DatabaseConfigurationManager.load_profile(),
            runtime_status=DatabaseConfigurationManager.runtime_status(),
            test_result=result,
            form_values=DatabaseConfigurationManager.load_profile() or {},
        )
