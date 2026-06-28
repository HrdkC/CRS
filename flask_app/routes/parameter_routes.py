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

        context = get_machine_stage_context_by_id(
            machine_id,
            stage_id,
            include_inactive=True
        )

        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/machines")

        back_url = machine_stage_url(
            "/parameters",
            context=context
        )

        if request.method == "POST":

            try:
                tag_index = int(
                    request.form.get("tag_index", "").strip()
                )
                plc_array_index = int(
                    request.form.get("plc_array_index", "").strip()
                )
                min_value = float(
                    request.form.get("min_value", "").strip()
                )
                max_value = float(
                    request.form.get("max_value", "").strip()
                )
                default_value = float(
                    request.form.get("default_value", "").strip()
                )
            except ValueError:
                flash(
                    "Tag index, PLC array index, min, max, and default value must be valid numbers.",
                    "error"
                )
                return render_template(
                    "parameters/add_parameter.html",
                    machine_id=machine_id,
                    stage_id=stage_id,
                    context=context,
                    back_url=back_url,
                    form_data=request.form
                )

            if max_value < min_value:
                flash(
                    "Max value cannot be lower than min value.",
                    "error"
                )
                return render_template(
                    "parameters/add_parameter.html",
                    machine_id=machine_id,
                    stage_id=stage_id,
                    context=context,
                    back_url=back_url,
                    form_data=request.form
                )

            ParameterDefinitionManager.create_parameter(

                machine_id=machine_id,

                stage_id=stage_id,

                tag_index=tag_index,

                plc_array_index=plc_array_index,

                parameter_name=(
                    request.form.get("parameter_name")
                    or
                    ""
                ).strip(),

                unit=(
                    request.form.get("unit")
                    or
                    ""
                ).strip(),

                min_value=min_value,

                max_value=max_value,

                default_value=default_value,

                created_by=session.get(
                    "username"
                )

            )

            flash(
                "Parameter Created"
            )

            return redirect(

                back_url

            )

        return render_template(

            "parameters/add_parameter.html",

            machine_id=machine_id,

            stage_id=stage_id,

            context=context,

            back_url=back_url

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

        if not parameter:
            flash("Parameter definition not found.", "error")
            return redirect("/recipes")

        context = get_machine_stage_context_by_id(
            parameter["machine_id"],
            parameter["stage_id"],
            include_inactive=True
        )

        back_url = machine_stage_url(
            "/parameters",
            machine_id=parameter["machine_id"],
            stage_id=parameter["stage_id"]
        )

        if request.method == "POST":

            try:
                min_value = float(
                    request.form.get("min_value", "").strip()
                )
                max_value = float(
                    request.form.get("max_value", "").strip()
                )
                default_value = float(
                    request.form.get("default_value", "").strip()
                )
            except ValueError:
                flash(
                    "Min, max, and default value must be valid numbers.",
                    "error"
                )
                return render_template(
                    "parameters/edit_parameter.html",
                    parameter=parameter,
                    context=context,
                    back_url=back_url,
                    form_data=request.form
                )

            if max_value < min_value:
                flash(
                    "Max value cannot be lower than min value.",
                    "error"
                )
                return render_template(
                    "parameters/edit_parameter.html",
                    parameter=parameter,
                    context=context,
                    back_url=back_url,
                    form_data=request.form
                )

            ParameterDefinitionManager.update_parameter(

                parameter_id=parameter_id,

                parameter_name=(
                    request.form.get("parameter_name")
                    or
                    ""
                ).strip(),

                unit=(
                    request.form.get("unit")
                    or
                    ""
                ).strip(),

                min_value=min_value,

                max_value=max_value,

                default_value=default_value

            )

            flash("Parameter updated.", "success")

            return redirect(

                back_url

            )

        return render_template(

            "parameters/edit_parameter.html",

            parameter=parameter,

            context=context,

            back_url=back_url

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
