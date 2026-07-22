import os

from flask_app import create_app

from flask_app.routes.auth_routes import register_auth_routes
from flask_app.routes.dashboard_routes import register_dashboard_routes
from flask_app.routes.user_routes import register_user_routes
from flask_app.routes.recipe_routes import register_recipe_routes
from flask_app.routes.audit_routes import register_audit_routes
from flask_app.routes.session_routes import register_session_routes
from flask_app.routes.machine_routes import register_machine_routes
from flask_app.routes.family_routes import register_family_routes
from flask_app.routes.plc_routes import register_plc_routes
from flask_app.routes.parameter_routes import register_parameter_routes
from flask_app.routes.plc_tag_routes import register_plc_tag_routes
from flask_app.routes.plc_array_import_routes import register_plc_array_import_routes
from flask_app.routes.recipe_editor_routes import register_recipe_editor_routes
from flask_app.routes.stage_routes import register_stage_routes
from flask_app.routes.help_routes import register_help_routes
from flask_app.routes.phase_control_routes import register_phase_control_routes
from flask_app.routes.configuration_routes import register_configuration_routes
from flask_app.routes.health_routes import register_health_routes
from flask_app.routes.database_configuration_routes import (
    register_database_configuration_routes,
)


def _env_enabled(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def should_use_waitress(deployment_mode: str) -> bool:
    """Choose the HTTP server independently from the security profile.

    Production security mode always uses Waitress.  Controlled intranet/trial
    installations may also request Waitress with ``CRS_USE_WAITRESS=1`` while
    HTTPS, trusted-host and secure-cookie commissioning is still pending.
    """

    return deployment_mode == "production" or _env_enabled(
        "CRS_USE_WAITRESS", "0"
    )


app = create_app()

register_auth_routes(app)
register_dashboard_routes(app)
register_user_routes(app)
register_recipe_routes(app)
register_audit_routes(app)
register_session_routes(app)
register_family_routes(app)
register_machine_routes(app)
register_stage_routes(app)
register_plc_routes(app)
register_plc_tag_routes(app)
register_plc_array_import_routes(app)
register_parameter_routes(app)
register_recipe_editor_routes(app)
register_help_routes(app)
register_phase_control_routes(app)
register_configuration_routes(app)
register_health_routes(app)
register_database_configuration_routes(app)


if __name__ == "__main__":
    from config.settings import DEPLOYMENT_MODE
    from utils.plc_worker_supervisor import PLCWorkerSupervisor

    debug_enabled = _env_enabled("CRS_FLASK_DEBUG", "0")
    reload_requested = _env_enabled("CRS_FLASK_RELOAD", "0")
    auto_worker_enabled = _env_enabled("CRS_AUTO_START_PLC_WORKER", "1")
    reload_enabled = reload_requested and not auto_worker_enabled
    use_waitress = should_use_waitress(DEPLOYMENT_MODE)

    app.config["TEMPLATES_AUTO_RELOAD"] = debug_enabled
    if debug_enabled:
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    supervisor = PLCWorkerSupervisor()
    worker_status = supervisor.start()

    print(f"CRS deployment/security mode: {DEPLOYMENT_MODE}", flush=True)
    print(
        f"CRS HTTP server: {'Waitress' if use_waitress else 'Flask development server'}",
        flush=True,
    )
    print(f"CRS Flask debug mode: {'ON' if debug_enabled else 'OFF'}", flush=True)
    print(f"CRS Python auto-reloader: {'ON' if reload_enabled else 'OFF'}", flush=True)
    print(worker_status.get("message", "PLC worker status unavailable."), flush=True)

    host = os.getenv("CRS_FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("CRS_FLASK_PORT", "5000"))

    try:
        if use_waitress:
            from waitress import serve

            threads = max(4, int(os.getenv("CRS_WAITRESS_THREADS", "8")))
            print(
                f"Starting CRS with Waitress on {host}:{port}; threads={threads}",
                flush=True,
            )
            serve(
                app,
                host=host,
                port=port,
                threads=threads,
                channel_timeout=int(
                    os.getenv("CRS_WAITRESS_CHANNEL_TIMEOUT", "120")
                ),
            )
        else:
            app.run(
                host=host,
                port=port,
                debug=debug_enabled,
                use_reloader=reload_enabled,
            )
    finally:
        supervisor.stop()
