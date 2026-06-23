from flask import (
    render_template,
    request,
    session,
    redirect,
    flash
)

from database.parameter_definition_manager import (
    ParameterDefinitionManager
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


def register_parameter_routes(app):

    @app.route(
        "/parameters/<int:machine_id>/<int:stage_id>"
    )
    def parameters(

        machine_id,

        stage_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        search_text = request.args.get(
            "search",
            ""
        )

        parameters = (

            ParameterDefinitionManager
            .search_parameters(

                machine_id=machine_id,

                stage_id=stage_id,

                search_text=search_text

            )

        )

        return render_template(

            "parameters/parameters.html",

            parameters=parameters,

            machine_id=machine_id,

            stage_id=stage_id,

            search_text=search_text

        )

    @app.route(
        "/parameters/add/<int:machine_id>/<int:stage_id>",
        methods=["GET", "POST"]
    )
    def add_parameter(

        machine_id,

        stage_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        if request.method == "POST":

            ParameterDefinitionManager.create_parameter(

                machine_id=machine_id,

                stage_id=stage_id,

                tag_index=int(
                    request.form["tag_index"]
                ),

                plc_array_index=int(
                    request.form["plc_array_index"]
                ),

                parameter_name=request.form[
                    "parameter_name"
                ],

                unit=request.form[
                    "unit"
                ],

                min_value=float(
                    request.form["min_value"]
                ),

                max_value=float(
                    request.form["max_value"]
                ),

                default_value=float(
                    request.form["default_value"]
                ),

                created_by=session.get(
                    "username"
                )

            )

            flash(
                "Parameter Created"
            )

            return redirect(

                f"/parameters/{machine_id}/{stage_id}"

            )

        return render_template(

            "parameters/add_parameter.html",

            machine_id=machine_id,

            stage_id=stage_id

        )

    @app.route(
        "/parameters/edit/<int:parameter_id>",
        methods=["GET", "POST"]
    )
    def edit_parameter(

        parameter_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        parameter = (

            ParameterDefinitionManager
            .get_parameter_by_id(

                parameter_id

            )

        )

        if request.method == "POST":

            ParameterDefinitionManager.update_parameter(

                parameter_id=parameter_id,

                parameter_name=request.form[
                    "parameter_name"
                ],

                unit=request.form[
                    "unit"
                ],

                min_value=float(
                    request.form["min_value"]
                ),

                max_value=float(
                    request.form["max_value"]
                ),

                default_value=float(
                    request.form["default_value"]
                )

            )

            return redirect(

                f"/parameters/{parameter['machine_id']}/{parameter['stage_id']}"

            )

        return render_template(

            "parameters/edit_parameter.html",

            parameter=parameter

        )

    @app.route(
        "/parameters/disable/<int:parameter_id>"
    )
    def disable_parameter(

        parameter_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        parameter = (

            ParameterDefinitionManager
            .get_parameter_by_id(

                parameter_id

            )

        )

        ParameterDefinitionManager.disable_parameter(

            parameter_id

        )

        return redirect(

            request.referrer

            or

            f"/parameters/{parameter['machine_id']}/{parameter['stage_id']}"

        )

    @app.route(
        "/parameters/enable/<int:parameter_id>"
    )
    def enable_parameter(

        parameter_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        parameter = (

            ParameterDefinitionManager
            .get_parameter_by_id(

                parameter_id

            )

        )

        ParameterDefinitionManager.enable_parameter(

            parameter_id

        )

        return redirect(

            request.referrer

            or

            f"/parameters/{parameter['machine_id']}/{parameter['stage_id']}"

        )