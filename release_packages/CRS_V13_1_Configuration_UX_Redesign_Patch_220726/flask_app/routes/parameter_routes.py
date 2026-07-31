import json

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

from database.audit_manager import (
    AuditManager
)

from database.parameter_template_setup_service import (
    ParameterTemplateSetupError,
    ParameterTemplateSetupService,
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

    parameter_scope = request.args.get(
        "parameter_scope",
        "active"
    )

    if parameter_scope not in [
        "active",
        "inactive",
        "all"
    ]:

        parameter_scope = "active"

    parameters = (

        ParameterDefinitionManager
        .search_parameters(

            machine_id=machine_id,

            stage_id=stage_id,

            search_text=search_text,

            parameter_scope=parameter_scope

        )

    )

    usage_counts = (
        ParameterDefinitionManager
        .get_usage_counts(
            machine_id,
            stage_id
        )
    )

    configured_array_tags = (
        ParameterTemplateSetupService
        .get_configured_array_tags(
            machine_id,
            stage_id
        )
    )

    default_array_tag_id = None
    for configured_tag in configured_array_tags:
        if configured_tag.get("recommended"):
            default_array_tag_id = configured_tag.get("id")
            break
    if default_array_tag_id is None and configured_array_tags:
        default_array_tag_id = configured_array_tags[0].get("id")

    name_prefix = " ".join(
        part
        for part in [
            str(context.get("machine_code") or "").upper(),
            str(context.get("stage_url_code") or context.get("stage_type") or "").upper(),
            "Parameter",
        ]
        if part
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

        template_setup_url=machine_stage_url("/parameters/template-setup", context=context),

        template_bulk_update_url=machine_stage_url("/parameters/bulk-update", context=context),

        configuration_url=machine_stage_url("/configuration", context=context),

        plc_array_import_url=machine_stage_url("/plc-array-import", context=context),

        configured_array_tags=configured_array_tags,

        default_array_tag_id=default_array_tag_id,

        default_name_prefix=name_prefix,

        search_text=search_text,

        parameter_scope=parameter_scope,

        active_parameter_count=usage_counts["active_count"],

        inactive_parameter_count=usage_counts["inactive_count"],

        total_parameter_count=usage_counts["total_count"]

    )


def register_parameter_routes(app):

    def _request_metadata():
        return {
            "user_agent": request.headers.get("User-Agent", ""),
            "forwarded_for": request.headers.get("X-Forwarded-For"),
            "request_host": request.host,
        }

    @app.route(
        "/parameters/setup-options/<machine_code>/<stage_code>",
        methods=["GET", "POST"],
    )
    def parameter_template_setup_options(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")
        context = get_machine_stage_context_by_code(machine_code, stage_code)
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")
        tags = ParameterTemplateSetupService.get_configured_array_tags(
            context["machine_id"], context["stage_id"]
        )
        recommended = next(
            (tag for tag in tags if tag.get("recommended")),
            tags[0] if tags else None,
        )
        preview = None
        copy_preview = None
        compatible_sources = ParameterTemplateSetupService.get_compatible_template_sources(
            context["machine_id"], context["stage_id"]
        )
        if request.method == "POST":
            try:
                if request.form.get("preview_method") == "copy":
                    copy_preview = ParameterTemplateSetupService.preview_copy(
                        context["machine_id"], context["stage_id"],
                        request.form.get("source_stage_id"),
                    )
                else:
                    preview = ParameterTemplateSetupService.preview_from_configured_array(
                        machine_id=context["machine_id"],
                        stage_id=context["stage_id"],
                        source_tag_id=request.form.get("source_tag_id"),
                        start_index=request.form.get("start_index"),
                        end_index=request.form.get("end_index"),
                        name_prefix=request.form.get("name_prefix"),
                        unit=request.form.get("unit"),
                        min_value=request.form.get("min_value"),
                        max_value=request.form.get("max_value"),
                        default_value=request.form.get("default_value"),
                    )
            except ParameterTemplateSetupError as exc:
                flash(str(exc), "error")
        stage_setup_url = machine_stage_url("/configuration", context=context) + "/setup?step=parameters"
        return render_template(
            "parameters/template_setup_options.html",
            context=context,
            configured_array_tags=tags,
            recommended_tag=recommended,
            preview=preview,
            copy_preview=copy_preview,
            compatible_sources=compatible_sources,
            stage_setup_url=stage_setup_url,
            create_url=machine_stage_url("/parameters/template-setup", context=context),
            parameters_url=machine_stage_url("/parameters", context=context),
            plc_import_url=machine_stage_url("/plc-array-import", context=context),
        )

    @app.route(
        "/parameters/copy-template/<machine_code>/<stage_code>",
        methods=["POST"],
    )
    def parameter_template_copy_named(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")
        context = get_machine_stage_context_by_code(machine_code, stage_code)
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")
        try:
            result = ParameterTemplateSetupService.copy_missing_from_stage(
                machine_id=context["machine_id"], stage_id=context["stage_id"],
                source_stage_id=request.form.get("source_stage_id"),
                username=session.get("username", "system"),
                role=session.get("role", "SYSTEM"),
                reason=request.form.get("reason"),
                request_metadata=_request_metadata(),
            )
            flash(
                f"Copied {result['created_count']} missing parameter row(s). Existing indexes were preserved.",
                "success",
            )
        except ParameterTemplateSetupError as exc:
            flash(str(exc), "error")
        if request.form.get("return_to") == "guided_setup":
            return redirect(
                machine_stage_url("/configuration", context=context)
                + "/setup?step=parameters"
            )
        return redirect(machine_stage_url("/parameters", context=context))

    @app.route(
        "/parameters/template-setup/<machine_code>/<stage_code>",
        methods=["POST"]
    )
    def parameter_template_setup_named(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(machine_code, stage_code)
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        back_url = machine_stage_url("/parameters", context=context)
        if request.form.get("return_to") == "guided_setup":
            back_url = (
                machine_stage_url("/configuration", context=context)
                + "/setup?step=parameters"
            )
        try:
            result = ParameterTemplateSetupService.create_missing_from_configured_array(
                machine_id=context["machine_id"],
                stage_id=context["stage_id"],
                source_tag_id=request.form.get("source_tag_id"),
                start_index=request.form.get("start_index"),
                end_index=request.form.get("end_index"),
                name_prefix=request.form.get("name_prefix"),
                unit=request.form.get("unit"),
                min_value=request.form.get("min_value"),
                max_value=request.form.get("max_value"),
                default_value=request.form.get("default_value"),
                username=session.get("username", "system"),
                role=session.get("role", "SYSTEM"),
                reason=request.form.get("reason"),
                request_metadata=_request_metadata(),
            )
        except ParameterTemplateSetupError as exc:
            flash(str(exc), "error")
            return redirect(back_url)
        except Exception:
            flash(
                "Parameter template setup could not be completed. No template rows were changed.",
                "error"
            )
            return redirect(back_url)

        if result.created_count:
            flash(
                f"Created {result.created_count} parameter template row(s) from "
                f"{result.source_tag_name}[{result.start_index}..{result.end_index}]. "
                "Review the generated names, units, limits, and defaults below before release.",
                "success"
            )
        else:
            flash(
                "No new rows were required. Existing parameter indexes were preserved.",
                "info"
            )
        if result.skipped_count:
            flash(
                f"{result.skipped_count} existing index(es) were skipped and not overwritten.",
                "warning"
            )
        return redirect(back_url)

    @app.route(
        "/parameters/bulk-update/<machine_code>/<stage_code>",
        methods=["POST"]
    )
    def parameter_template_bulk_update_named(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(machine_code, stage_code)
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        back_url = machine_stage_url(
            "/parameters",
            context=context,
            query={
                "search": request.form.get("return_search", ""),
                "parameter_scope": request.form.get("return_scope", "active"),
            }
        )

        try:
            payload = json.loads(request.form.get("changes_json") or "[]")
            if not isinstance(payload, list):
                raise ParameterTemplateSetupError("Invalid parameter change payload.")
            result = ParameterTemplateSetupService.bulk_update_template(
                machine_id=context["machine_id"],
                stage_id=context["stage_id"],
                changes=payload,
                username=session.get("username", "system"),
                role=session.get("role", "SYSTEM"),
                reason=request.form.get("reason"),
                request_metadata=_request_metadata(),
            )
        except (json.JSONDecodeError, ParameterTemplateSetupError) as exc:
            flash(str(exc), "error")
            return redirect(back_url)
        except Exception:
            flash(
                "Parameter template changes could not be saved. No rows were changed.",
                "error"
            )
            return redirect(back_url)

        flash(
            f"Saved {result.changed_count} changed parameter row(s).",
            "success"
        )
        if result.backfilled_value_count:
            flash(
                f"Backfilled {result.backfilled_value_count} missing recipe value row(s) for parameters restored to Used.",
                "info"
            )
        return redirect(back_url)

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
        "/parameters/disable/<int:parameter_id>",
        methods=["POST"]
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

        if not parameter:

            flash("Parameter definition not found.", "error")
            return redirect("/configuration")

        ParameterDefinitionManager.disable_parameter(

            parameter_id

        )

        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PARAMETER_MARKED_NOT_USED",
            change_source="PARAMETER_TEMPLATE",
            record_id=parameter_id,
            parameter_name=parameter.get("parameter_name"),
            old_value="used=1",
            new_value="used=0",
            reason=(
                "Parameter removed from active module template. "
                "Existing stored values are retained for history."
            ),
            user_agent=request.headers.get("User-Agent", ""),
            forwarded_for=request.headers.get("X-Forwarded-For"),
            request_host=request.host
        )

        flash(
            "Parameter marked Not Used. Existing recipe values were retained and normal download validation will ignore this parameter.",
            "success"
        )

        return redirect(

            request.referrer

            or

            machine_stage_url("/parameters", machine_id=parameter["machine_id"], stage_id=parameter["stage_id"])

        )

    @app.route(
        "/parameters/enable/<int:parameter_id>",
        methods=["POST"]
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

        if not parameter:

            flash("Parameter definition not found.", "error")
            return redirect("/configuration")

        ParameterDefinitionManager.enable_parameter(

            parameter_id

        )

        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PARAMETER_MARKED_USED",
            change_source="PARAMETER_TEMPLATE",
            record_id=parameter_id,
            parameter_name=parameter.get("parameter_name"),
            old_value="used=0",
            new_value="used=1",
            reason=(
                "Parameter restored to active module template. "
                "Missing values were backfilled to existing recipes."
            ),
            user_agent=request.headers.get("User-Agent", ""),
            forwarded_for=request.headers.get("X-Forwarded-For"),
            request_host=request.host
        )

        flash(
            "Parameter restored as Used. Missing values were backfilled to existing recipes for this machine/stage.",
            "success"
        )

        return redirect(

            request.referrer

            or

            machine_stage_url("/parameters", machine_id=parameter["machine_id"], stage_id=parameter["stage_id"])

        )
