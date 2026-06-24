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
from flask_app.routes.recipe_editor_routes import register_recipe_editor_routes
from flask_app.routes.stage_routes import register_stage_routes


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
register_parameter_routes(app)
register_recipe_editor_routes(app)


if __name__ == "__main__":
    debug_enabled = os.getenv("CRS_FLASK_DEBUG", "0").strip() in {"1", "true", "TRUE", "yes", "YES"}
    app.run(
        host=os.getenv("CRS_FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("CRS_FLASK_PORT", "5000")),
        debug=debug_enabled,
        use_reloader=debug_enabled,
    )
