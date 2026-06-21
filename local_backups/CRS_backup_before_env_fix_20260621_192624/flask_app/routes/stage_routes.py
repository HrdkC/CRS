from flask import (
    render_template,
    redirect,
    session
)

from database.stage_manager import (
    StageManager
)


def register_stage_routes(app):

    @app.route("/stages")
    def stages():

        if session.get("role") != "ADMIN":

            return redirect("/")

        stages = (
            StageManager
            .get_all_stages_with_machine()
        )

        return render_template(

            "stages/stages.html",

            stages=stages

        )