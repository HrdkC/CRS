from flask import (
    render_template,
    redirect,
    session
)

from database.stage_manager import (
    StageManager
)


from flask_app.security.role_guard import (
    role_can
)


def _engineering_config_allowed():
    return (
        session.get("logged_in")
        and
        role_can(
            session.get("role"),
            "engineering_config"
        )
    )


def register_stage_routes(app):

    @app.route("/stages")
    def stages():

        if not _engineering_config_allowed():

            return redirect("/")

        stages = (
            StageManager
            .get_all_stages_with_machine()
        )

        return render_template(

            "stages/stages.html",

            stages=stages

        )