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

from flask_app.stage_url_helper import (
    get_machine_stage_context_by_code,
    get_machine_stage_context_by_id,
    machine_stage_url,
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


def _render_parameters_page(context):

    if not _engineering_config_allowed():

        return redirect("/")

    machine_id = context["machine_id"]
    stage_id = context["stage_id"]

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

        context=context,

        machine_code=context.get("machine_code"),

        stage_type=context.get("stage_type"),

        machine_stage_title=context.get("machine_stage_display"),

        parameters_url=machine_stage_url("/parameters", context=context),

        add_parameter_url=machine_stage_url("/parameters/add", context=context),

        search_text=search_text

    )


def register_parameter_routes(app):

    @app.route(
        "/parameters/<machine_code>/<stage_code>"
    )
    def parameters_named(

        machine_code,

        stage_code

    ):

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code
        )

        if not context:
            flash(
                "Machine/stage not found. Use friendly route like /parameters/P15/FS or /parameters/P15/SS.",
                "error"
            )
            return redirect("/machines")

        canonical_url = machine_stage_url(
            "/parameters",
            context=context,
            query=request.args
        )
        current_path = f"/parameters/{machine_code}/{stage_code}"
        if current_path != canonical_url.split("?")[0]:
            return redirect(canonical_url)

        return _render_parameters_page(context)

    @app.route(
        "/parameters/<int:machine_id>/<int:stage_id>"
    )
    def parameters(

        machine_id,

        stage_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        context = get_machine_stage_context_by_id(
            machine_id,
            stage_id,
            include_inactive=True
        )

        if context:
            return redirect(
                machine_stage_url(
                    "/parameters",
                    context=context,
                    query=request.args
                )
            )

        flash("Machine/stage not found.", "error")
        return redirect("/machines")


    @app.route(
        "/parameters/add/<machine_code>/<stage_code>",
        methods=["GET", "POST"]
    )
    def add_parameter_named(

        machine_code,

        stage_code

    ):

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code
        )

        if not context:
            flash(
                "Machine/stage not found. Use friendly route like /parameters/add/P15/FS or /parameters/add/P15/SS.",
                "error"
            )
            return redirect("/machines")

        return add_parameter(
            context["machine_id"],
            context["stage_id"]
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

                machine_stage_url("/parameters", machine_id=machine_id, stage_id=stage_id)

            )

        return render_template(

            "parameters/add_parameter.html",

            machine_id=machine_id,

            stage_id=stage_id,

            context=get_machine_stage_context_by_id(machine_id, stage_id, include_inactive=True),

            back_url=machine_stage_url("/parameters", machine_id=machine_id, stage_id=stage_id)

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

                machine_stage_url("/parameters", machine_id=parameter["machine_id"], stage_id=parameter["stage_id"])

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

            machine_stage_url("/parameters", machine_id=parameter["machine_id"], stage_id=parameter["stage_id"])

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

            machine_stage_url("/parameters", machine_id=parameter["machine_id"], stage_id=parameter["stage_id"])

        )