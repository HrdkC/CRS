import os
import re
from datetime import timedelta

from flask import Flask, render_template, session

from config.settings import (
    APP_VERSION,
    DEPLOYMENT_MODE,
    SECRET_KEY,
    SECRET_KEY_FALLBACKS,
    SESSION_TIMEOUT_MINUTES,
    TRUSTED_HOSTS,
)
from flask_app.security.security_headers import secure_cookie_enabled


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    if (
        DEPLOYMENT_MODE == "production"
        and SECRET_KEY == "crs_secret_key"
    ):
        raise RuntimeError(
            "CRS_SECRET_KEY must be configured before production deployment."
        )

    app.secret_key = SECRET_KEY

    cookie_secure = secure_cookie_enabled()
    if DEPLOYMENT_MODE == "production" and not cookie_secure:
        raise RuntimeError(
            "CRS_COOKIE_SECURE must be enabled for production deployment."
        )
    if DEPLOYMENT_MODE == "production" and not TRUSTED_HOSTS:
        raise RuntimeError(
            "CRS_TRUSTED_HOSTS must list the production hostname or IP."
        )

    try:
        max_upload_mb = int(os.getenv("CRS_MAX_UPLOAD_MB", "25"))
    except (TypeError, ValueError):
        max_upload_mb = 25

    try:
        max_form_memory_mb = int(
            os.getenv("CRS_MAX_FORM_MEMORY_MB", "2")
        )
    except (TypeError, ValueError):
        max_form_memory_mb = 2

    try:
        max_form_parts = int(os.getenv("CRS_MAX_FORM_PARTS", "1000"))
    except (TypeError, ValueError):
        max_form_parts = 1000

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE=os.getenv("CRS_SESSION_COOKIE_SAMESITE", "Strict"),
        SESSION_COOKIE_SECURE=cookie_secure,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=SESSION_TIMEOUT_MINUTES),
        MAX_CONTENT_LENGTH=max(1, max_upload_mb) * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=max(1, max_form_memory_mb) * 1024 * 1024,
        MAX_FORM_PARTS=max(100, max_form_parts),
        TRUSTED_HOSTS=TRUSTED_HOSTS or None,
        SECRET_KEY_FALLBACKS=SECRET_KEY_FALLBACKS or None,
        PREFERRED_URL_SCHEME="https" if cookie_secure else "http",
    )

    if SECRET_KEY == "crs_secret_key":
        print(
            "WARNING: CRS_SECRET_KEY is using the development fallback. "
            "Set CRS_SECRET_KEY before plant deployment."
        )

    from flask_app.security.security_headers import register_security_headers
    register_security_headers(app)

    from flask_app.security.csrf import register_csrf_protection
    register_csrf_protection(app)

    startup_mutations_default = (
        "0" if DEPLOYMENT_MODE == "production" else "1"
    )
    startup_mutations_allowed = os.getenv(
        "CRS_ALLOW_STARTUP_MIGRATIONS",
        startup_mutations_default,
    ).strip().lower() in {"1", "true", "yes", "on"}

    if startup_mutations_allowed:
        try:
            from database.upgrade_user_management_priority11 import (
                upgrade_user_management_schema
            )
            upgrade_user_management_schema()
        except Exception as exc:
            print("Priority 11 schema upgrade skipped/failed:", exc)

        try:
            from database.phase_control_default_manager import (
                PhaseControlDefaultManager
            )
            PhaseControlDefaultManager.initialize_all_stages()
        except Exception as exc:
            print("Phase control default sync skipped/failed:", exc)

    from flask_app.security.session_guard import register_session_guard
    register_session_guard(app)

    @app.context_processor
    def inject_role_helpers():
        import time

        from database.system_settings_manager import SystemSettingsManager

        from flask_app.security.role_guard import (
            role_can as _role_can,
            role_label as _role_label,
            is_admin_role as _is_admin_role
        )

        def can(capability):
            return _role_can(
                session.get("role"),
                capability
            )

        def current_role_label():
            return _role_label(
                session.get("role")
            )

        def is_admin():
            return _is_admin_role(
                session.get("role")
            )

        def display_username(username):
            parts = re.split(r"[\s._-]+", (username or "").strip())
            return " ".join(part[:1].upper() + part[1:].lower() for part in parts if part)

        try:
            session_timeout_minutes = (
                SystemSettingsManager.get_session_timeout_minutes()
            )
        except Exception:
            session_timeout_minutes = 30

        from flask_app.stage_url_helper import (
            stage_url_code,
            stage_display_name,
            machine_stage_display,
            machine_stage_path,
            machine_stage_url,
        )

        return {
            "role_can": can,
            "current_role_label": current_role_label,
            "is_admin": is_admin,
            "display_username": display_username,
            "session_timeout_minutes": session_timeout_minutes,
            "session_timeout_seconds": session_timeout_minutes * 60,
            "current_epoch": int(time.time()),
            "stage_url_code": stage_url_code,
            "stage_display_name": stage_display_name,
            "machine_stage_display": machine_stage_display,
            "machine_stage_path": machine_stage_path,
            "machine_stage_url": machine_stage_url,
            "app_version": APP_VERSION,
        }

    @app.errorhandler(404)
    def page_not_found(error):
        return (
            render_template(
                "errors/error.html",
                status_code=404,
                title="Page Not Found",
                message=(
                    "This CRS page or link is not available. "
                    "Use Back or Dashboard and report the missing link if it repeats."
                ),
                technical_detail=(
                    str(error)
                    if session.get("role") == "ADMIN"
                    else
                    ""
                ),
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.exception(
            "Unhandled CRS server error",
            exc_info=True
        )
        return (
            render_template(
                "errors/error.html",
                status_code=500,
                title="CRS Server Error",
                message=(
                    "The requested operation could not be completed safely. "
                    "No PLC download should be assumed complete unless the operation history shows success."
                ),
                technical_detail=(
                    str(error)
                    if session.get("role") == "ADMIN"
                    else
                    ""
                ),
            ),
            500,
        )

    return app
