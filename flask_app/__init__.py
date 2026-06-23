from flask import Flask, session

from config.settings import SECRET_KEY


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    app.secret_key = SECRET_KEY

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax"
    )

    try:
        from database.upgrade_user_management_priority11 import (
            upgrade_user_management_schema
        )
        upgrade_user_management_schema()
    except Exception as exc:
        print("Priority 11 schema upgrade skipped/failed:", exc)

    try:
        from flask_app.security.session_guard import register_session_guard
        register_session_guard(app)
    except Exception as exc:
        print("Session guard registration failed:", exc)

    @app.context_processor
    def inject_role_helpers():
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

        return {
            "role_can": can,
            "current_role_label": current_role_label,
            "is_admin": is_admin
        }

    return app
