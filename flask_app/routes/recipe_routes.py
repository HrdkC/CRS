from flask import render_template, session, redirect, request, flash, send_file

from database.recipe_manager import RecipeManager
from database.database import get_connection

from database.audit_manager import AuditManager

from helper.datetime_helper import (
    utc_to_ist
)

from flask_app.security.role_guard import (
    role_can
)

from flask_app.stage_url_helper import (
    add_machine_stage_url_fields,
    machine_stage_display,
    machine_stage_url,
    normalize_stage_type,
    stage_display_name,
    stage_url_code,
)


def _is_historical_recipe(recipe):

    return (
        recipe
        and
        recipe.get("version_usage_status")
        == "HISTORY_RELEASED"
    )


def _is_legacy_historical_version(recipe, selected_version):

    if not recipe:
        return False

    try:
        selected_version = int(selected_version)
        current_version = int(recipe.get("current_version"))
    except Exception:
        return False

    return selected_version != current_version



def _engineering_config_allowed():
    return (
        session.get("logged_in")
        and
        role_can(
            session.get("role"),
            "engineering_config"
        )
    )



def _friendly_stage_path(stage_type):
    """Return URL-friendly stage code, e.g. FIRST_STAGE -> FS, SECOND_STAGE -> SS."""
    return stage_url_code(stage_type)


def _normalize_stage_path(stage_path):
    """Accept FS/SS and older First_Stage/Second_Stage style URLs."""
    return normalize_stage_type(stage_path)


def _resolve_machine_stage_by_code(machine_code, stage_path):
    """Resolve /recipes/P15/FS or /recipes/P15/SS into machine/stage IDs."""
    normalized_stage = _normalize_stage_path(stage_path)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            m.id AS machine_id,
            m.machine_code,
            m.description AS machine_description,
            s.id AS stage_id,
            s.stage_type,
            s.description AS stage_description
        FROM tbm_machines m
        INNER JOIN machine_stages s
            ON s.machine_id = m.id
        WHERE
            UPPER(m.machine_code) = UPPER(?)
            AND UPPER(s.stage_type) = UPPER(?)
            AND COALESCE(m.active, 1) = 1
            AND COALESCE(s.active, 1) = 1
        """,
        (machine_code, normalized_stage)
    )
    row = cursor.fetchone()
    conn.close()
    return add_machine_stage_url_fields(dict(row)) if row else None


def _resolve_machine_stage_by_id(machine_id, stage_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            m.id AS machine_id,
            m.machine_code,
            m.description AS machine_description,
            s.id AS stage_id,
            s.stage_type,
            s.description AS stage_description
        FROM tbm_machines m
        INNER JOIN machine_stages s
            ON s.machine_id = m.id
        WHERE
            m.id = ?
            AND s.id = ?
            AND COALESCE(m.active, 1) = 1
            AND COALESCE(s.active, 1) = 1
        """,
        (machine_id, stage_id)
    )
    row = cursor.fetchone()
    conn.close()
    return add_machine_stage_url_fields(dict(row)) if row else None


def _parameter_definition_count(machine_id, stage_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM parameter_definitions
        WHERE machine_id = ? AND stage_id = ? AND COALESCE(used, 1) = 1
        """,
        (machine_id, stage_id)
    )
    row = cursor.fetchone()
    conn.close()
    return int(row["total"] if row else 0)


def _machine_stage_targets():
    """Return active machine/stage choices for recipe list selection."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            m.id AS machine_id,
            m.machine_code,
            m.description AS machine_description,
            s.id AS stage_id,
            s.stage_type,
            s.description AS stage_description
        FROM tbm_machines m
        INNER JOIN machine_stages s
            ON s.machine_id = m.id
        WHERE
            COALESCE(m.active, 1) = 1
            AND COALESCE(s.active, 1) = 1
        ORDER BY
            m.machine_code,
            CASE UPPER(s.stage_type)
                WHEN 'FIRST_STAGE' THEN 1
                WHEN 'SECOND_STAGE' THEN 2
                ELSE 99
            END,
            s.stage_type
        """
    )
    rows = [add_machine_stage_url_fields(dict(row)) for row in cursor.fetchall()]
    conn.close()

    for row in rows:
        row["recipe_list_url"] = _friendly_recipe_list_url(row)

    return rows


def _render_recipe_list_page(ctx=None, recipes=None):
    """Render recipe list only after machine/stage selection."""
    recipes = recipes or []
    targets = _machine_stage_targets()
    machine_seen = set()
    machine_options = []
    for target in targets:
        machine_key = target.get("machine_id")
        if machine_key in machine_seen:
            continue
        machine_seen.add(machine_key)
        machine_options.append({
            "machine_id": target.get("machine_id"),
            "machine_code": target.get("machine_code"),
            "machine_description": target.get("machine_description"),
        })

    template_data = {
        "recipes": recipes,
        "machine_stage_targets": targets,
        "machine_stage_machine_options": machine_options,
        "has_stage_selection": bool(ctx),
    }

    if ctx:
        parameter_count = _parameter_definition_count(ctx["machine_id"], ctx["stage_id"])
        template_data.update({
            "context": ctx,
            "machine_id": ctx["machine_id"],
            "stage_id": ctx["stage_id"],
            "machine_code": ctx["machine_code"],
            "stage_type": ctx["stage_type"],
            "stage_path": _friendly_stage_path(ctx["stage_type"]),
            "stage_url_code": stage_url_code(ctx["stage_type"]),
            "stage_display_name": stage_display_name(ctx["stage_type"]),
            "machine_stage_title": machine_stage_display(context=ctx),
            "selected_machine_id": ctx["machine_id"],
            "selected_stage_id": ctx["stage_id"],
            "selected_recipe_list_url": _friendly_recipe_list_url(ctx),
            "create_url": _friendly_recipe_create_url(ctx),
            "parameter_count": parameter_count,
            "parameter_master_ready": (parameter_count > 0),
            "plc_tag_browser_url": machine_stage_url(
                "/plc-tags",
                context=ctx,
                query={
                    "online_search": "1",
                    "search": "",
                    "array_only": "1",
                    "bool_only": "0",
                }
            ),
            "plc_array_import_url": machine_stage_url("/plc-array-import", context=ctx),
        })

    return render_template("recipes/recipes.html", **template_data)


def _friendly_recipe_list_url(ctx):
    return f"/recipes/{ctx['machine_code']}/{_friendly_stage_path(ctx['stage_type'])}"


def _friendly_recipe_create_url(ctx):
    return f"/recipes/create/{ctx['machine_code']}/{_friendly_stage_path(ctx['stage_type'])}"


def _render_create_recipe_page(ctx):
    parameter_count = _parameter_definition_count(ctx["machine_id"], ctx["stage_id"])
    return render_template(
        "recipes/create_recipe.html",
        machine_id=ctx["machine_id"],
        stage_id=ctx["stage_id"],
        context=ctx,
        machine_code=ctx["machine_code"],
        stage_type=ctx["stage_type"],
        stage_path=_friendly_stage_path(ctx["stage_type"]),
        stage_url_code=stage_url_code(ctx["stage_type"]),
        stage_display_name=stage_display_name(ctx["stage_type"]),
        machine_stage_title=machine_stage_display(context=ctx),
        parameter_count=parameter_count,
        parameter_master_ready=(parameter_count > 0),
        back_url=_friendly_recipe_list_url(ctx),
        create_url=_friendly_recipe_create_url(ctx),
        plc_tag_browser_url=machine_stage_url(
            "/plc-tags",
            context=ctx,
            query={
                "online_search": "1",
                "search": "",
                "array_only": "1",
                "bool_only": "0",
            }
        ),
        plc_array_import_url=machine_stage_url("/plc-array-import", context=ctx),
    )


def _handle_create_recipe_post(ctx):
    parameter_count = _parameter_definition_count(ctx["machine_id"], ctx["stage_id"])
    if parameter_count <= 0:
        flash(
            (
                f"Cannot create recipe for {ctx['machine_code']} {ctx['stage_type']}. "
                "Parameter master is not configured. Build/import parameter master first."
            ),
            "warning"
        )
        return redirect(_friendly_recipe_create_url(ctx))

    recipe_code = (request.form.get("recipe_code") or "").strip()
    recipe_name = (request.form.get("recipe_name") or "").strip()

    if not recipe_code or not recipe_name:
        flash("Recipe code and recipe name are required.", "error")
        return redirect(_friendly_recipe_create_url(ctx))

    try:
        recipe_id = RecipeManager.create_recipe(
            machine_id=ctx["machine_id"],
            stage_id=ctx["stage_id"],
            recipe_code=recipe_code,
            recipe_name=recipe_name,
            created_by=session["username"]
        )
    except Exception as exc:
        flash(f"Recipe creation failed: {exc}", "error")
        return redirect(_friendly_recipe_create_url(ctx))

    flash(f"Recipe Created: {recipe_code.upper()}", "success")
    return redirect(f"/recipe-editor/{recipe_id}")

def register_recipe_routes(app):

    @app.route("/recipes")
    def recipes():

        if not session.get("logged_in"):
            return redirect("/login")

        # Legacy/query based selection support:
        # /recipes?machine_id=5&stage_id=12 -> /recipes/P15/SS
        machine_id = request.args.get("machine_id", type=int)
        stage_id = request.args.get("stage_id", type=int)
        if machine_id and stage_id:
            ctx = _resolve_machine_stage_by_id(machine_id, stage_id)
            if ctx:
                return redirect(_friendly_recipe_list_url(ctx))
            flash("Machine/stage not found or inactive.", "error")

        # No mixed recipe list on the main page.
        # Operator must select machine/stage first.
        return _render_recipe_list_page()

    @app.route("/recipes/import-export")
    def recipe_import_export_page():

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "recipe_view"):
            flash("Your role cannot view recipe import/export.", "error")
            return redirect("/")

        from database.recipe_excel_import_export_manager import (
            RecipeExcelImportExportManager
        )

        targets = RecipeExcelImportExportManager.get_template_targets()

        recipe_options = RecipeExcelImportExportManager.get_import_recipe_options()

        return render_template(
            "recipes/recipe_import_export.html",
            targets=targets,
            recipe_options=recipe_options,
            preview=None,
            token=None
        )

    @app.route("/recipes/<int:recipe_id>/export-excel")
    def recipe_export_excel(recipe_id):

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "recipe_view"):
            flash("Your role cannot export recipes.", "error")
            return redirect("/recipes")

        from database.recipe_excel_import_export_manager import (
            RecipeExcelImportExportManager
        )

        try:
            workbook, recipe = RecipeExcelImportExportManager.build_export_workbook(
                recipe_id=recipe_id,
                exported_by=session.get("username")
            )
            stream = RecipeExcelImportExportManager.workbook_to_bytes(workbook)
            file_name = RecipeExcelImportExportManager.export_filename(recipe)

            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action="RECIPE_EXPORTED_EXCEL",
                change_source="WEB_RECIPE_IMPORT_EXPORT",
                recipe_code=recipe.get("recipe_code"),
                recipe_version=recipe.get("version"),
                record_id=recipe_id,
                new_value=file_name,
                reason="Recipe exported with parameters and phase control"
            )

            return send_file(
                stream,
                as_attachment=True,
                download_name=file_name,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as exc:
            flash(f"Recipe export failed: {exc}", "error")
            return redirect(f"/recipe-editor/{recipe_id}")

    @app.route("/recipes/import-template-excel")
    def recipe_import_template_excel():

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "recipe_edit"):
            flash("Your role cannot download import templates.", "error")
            return redirect("/recipes/import-export")

        from database.recipe_excel_import_export_manager import (
            RecipeExcelImportExportManager
        )

        machine_id = request.args.get("machine_id", type=int)
        stage_id = request.args.get("stage_id", type=int)

        if not machine_id or not stage_id:
            flash("Select machine/stage before downloading import template.", "warning")
            return redirect("/recipes/import-export")

        try:
            workbook, target = RecipeExcelImportExportManager.build_blank_template_workbook(
                machine_id=machine_id,
                stage_id=stage_id,
                exported_by=session.get("username")
            )
            stream = RecipeExcelImportExportManager.workbook_to_bytes(workbook)
            file_name = RecipeExcelImportExportManager.template_filename(target)

            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action="RECIPE_IMPORT_TEMPLATE_DOWNLOADED",
                change_source="WEB_RECIPE_IMPORT_EXPORT",
                new_value=file_name,
                reason=f"Template target machine={machine_id}; stage={stage_id}"
            )

            return send_file(
                stream,
                as_attachment=True,
                download_name=file_name,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as exc:
            flash(f"Template download failed: {exc}", "error")
            return redirect("/recipes/import-export")

    @app.route("/recipes/import-preview", methods=["POST"])
    def recipe_import_preview():

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "recipe_edit"):
            flash("Your role cannot import recipes.", "error")
            return redirect("/recipes/import-export")

        from database.recipe_excel_import_export_manager import (
            RecipeExcelImportExportManager
        )

        try:
            token, file_path = RecipeExcelImportExportManager.save_pending_upload(
                request.files.get("recipe_file")
            )
            preview = RecipeExcelImportExportManager.preview_import(
                file_path,
                machine_id=request.form.get("machine_id", type=int),
                stage_id=request.form.get("stage_id", type=int),
                recipe_code_override=request.form.get("recipe_code"),
                recipe_name_override=request.form.get("recipe_name"),
                import_mode=request.form.get("import_mode"),
                existing_recipe_id=request.form.get("existing_recipe_id", type=int),
                update_master_details=request.form.get("update_master_details"),
                mark_missing_parameters_not_used=request.form.get("mark_missing_parameters_not_used")
            )
        except Exception as exc:
            flash(str(exc), "error")
            return redirect("/recipes/import-export")

        targets = RecipeExcelImportExportManager.get_template_targets()
        recipe_options = RecipeExcelImportExportManager.get_import_recipe_options()

        if preview.get("ok"):
            if preview.get("summary", {}).get("import_mode") == "update_existing":
                flash("Import preview passed. Confirm to update the selected existing recipe parameters.", "success")
            else:
                flash("Import preview passed. Confirm to save recipe as DRAFT.", "success")
        else:
            flash("Import preview failed. Correct the Excel file and upload again.", "error")

        return render_template(
            "recipes/recipe_import_export.html",
            targets=targets,
            recipe_options=recipe_options,
            preview=preview,
            token=token
        )

    @app.route("/recipes/import-confirm", methods=["POST"])
    def recipe_import_confirm():

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "recipe_edit"):
            flash("Your role cannot import recipes.", "error")
            return redirect("/recipes/import-export")

        from database.recipe_excel_import_export_manager import (
            RecipeExcelImportExportManager
        )

        token = request.form.get("token")
        reason = (request.form.get("reason") or "").strip()
        machine_id = request.form.get("machine_id", type=int)
        stage_id = request.form.get("stage_id", type=int)
        recipe_code_override = request.form.get("recipe_code")
        recipe_name_override = request.form.get("recipe_name")
        import_mode = request.form.get("import_mode")
        existing_recipe_id = request.form.get("existing_recipe_id", type=int)
        update_master_details = request.form.get("update_master_details")
        mark_missing_parameters_not_used = request.form.get("mark_missing_parameters_not_used")

        try:
            success, recipe_id, preview = RecipeExcelImportExportManager.import_pending_file(
                token=token,
                imported_by=session.get("username"),
                user_role=session.get("role"),
                reason=reason or "Recipe imported from Excel template",
                request_obj=request,
                machine_id=machine_id,
                stage_id=stage_id,
                recipe_code_override=recipe_code_override,
                recipe_name_override=recipe_name_override,
                import_mode=import_mode,
                existing_recipe_id=existing_recipe_id,
                update_master_details=update_master_details,
                mark_missing_parameters_not_used=mark_missing_parameters_not_used
            )
        except Exception as exc:
            flash(f"Recipe import failed: {exc}", "error")
            return redirect("/recipes/import-export")

        if not success:
            flash("Recipe import failed validation. Correct the Excel file and upload again.", "error")
            targets = RecipeExcelImportExportManager.get_template_targets()
            recipe_options = RecipeExcelImportExportManager.get_import_recipe_options()
            return render_template(
                "recipes/recipe_import_export.html",
                targets=targets,
                recipe_options=recipe_options,
                preview=preview,
                token=token
            )

        if (preview.get("summary") or {}).get("import_mode") == "update_existing":
            flash("Existing recipe parameters updated from Excel with audit. Review values before PLC use.", "success")
        else:
            flash("Recipe imported successfully as DRAFT. Review values before release or PLC use.", "success")
        return redirect(f"/recipe-editor/{recipe_id}")

    @app.route(
        "/recipes/create/<int:machine_id>/<int:stage_id>",
        methods=["GET", "POST"]
    )
    def create_recipe(machine_id, stage_id):

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "recipe_edit"):
            flash("Your role cannot create recipes.", "error")
            return redirect(machine_stage_url("/recipes", machine_id=machine_id, stage_id=stage_id))

        ctx = _resolve_machine_stage_by_id(machine_id, stage_id)
        if not ctx:
            flash("Machine/stage not found or inactive.", "error")
            return redirect("/recipes")

        # Numeric route remains supported for backward compatibility.
        # GET redirects to the operator-friendly URL such as:
        # /recipes/create/P15/SS
        if request.method == "GET":
            return redirect(_friendly_recipe_create_url(ctx))

        return _handle_create_recipe_post(ctx)

    @app.route(
        "/recipes/create/<machine_code>/<stage_path>",
        methods=["GET", "POST"]
    )
    def create_recipe_named(machine_code, stage_path):

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(session.get("role"), "recipe_edit"):
            flash("Your role cannot create recipes.", "error")
            return redirect("/recipes")

        ctx = _resolve_machine_stage_by_code(machine_code, stage_path)
        if not ctx:
            flash("Machine/stage not found. Use machine code and stage name, e.g. /recipes/create/P15/SS.", "error")
            return redirect("/recipes")

        if request.method == "POST":
            return _handle_create_recipe_post(ctx)

        canonical_url = _friendly_recipe_create_url(ctx)
        current_path = f"/recipes/create/{machine_code}/{stage_path}"
        if current_path != canonical_url:
            return redirect(canonical_url)

        return _render_create_recipe_page(ctx)

    @app.route("/recipes/<recipe_code>")
    def recipe_details(recipe_code):

        if not session.get("logged_in"):
            return redirect("/login")

        recipe = RecipeManager.get_recipe(
            recipe_code
        )

        if not recipe:

            flash(
                "Recipe not found.",
                "error"
            )

            return redirect("/recipes")

        return render_template(
            "recipes/recipe_details.html",
            recipe=recipe
        )
    
    @app.route(
        "/recipes/<recipe_code>/create-version"
    )
    def create_recipe_version(
        recipe_code
    ):

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(
            session.get("role"),
            "recipe_edit"
        ):

            return redirect("/recipes")

        recipe = RecipeManager.get_recipe(
            recipe_code
        )

        source_version = recipe[
            "current_version"
        ]

        new_version = RecipeManager.create_recipe_version(

            recipe_code=recipe_code,

            source_version=source_version,

            created_by=session["username"]

        )

        flash(
            f"{recipe_code} Version {new_version} Created",
            "success"
        )

        return redirect(
            f"/recipes/{recipe_code}"
        )

    @app.route("/recipes/<recipe_code>/parameters")
    def recipe_parameters(recipe_code):

        if not session.get("logged_in"):
            return redirect("/login")

        recipe = RecipeManager.get_recipe(
            recipe_code
        )

        if not recipe:

            flash(
                "Recipe not found.",
                "error"
            )

            return redirect("/recipes")

        versions = RecipeManager.get_recipe_versions(
            recipe_code
        )

        selected_version = request.args.get(
            "version",
            type=int
        )

        if not selected_version:

            selected_version = recipe[
                "current_version"
            ]

        parameters = RecipeManager.get_recipe_parameters(

            recipe_code,

            selected_version

        )

        version_info = RecipeManager.get_version_details(

            recipe_code,

            selected_version

        )

        if version_info:

            version_info["display_created_at"] = (
                utc_to_ist(
                    version_info["created_at"]
                )
            )

        return render_template(

            "recipes/recipe_parameters.html",

            recipe_code=recipe_code,

            parameters=parameters,

            versions=versions,

            selected_version=selected_version,

            version_info=version_info

        )
    
    @app.route(
        "/recipes/<recipe_code>/parameters/<parameter_name>/edit",
        methods=["GET", "POST"]
    )
    def edit_parameter_value(
        recipe_code,
        parameter_name
    ):

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(
            session.get("role"),
            "recipe_edit"
        ):

            return redirect("/recipes")

        selected_version = request.args.get(
            "version",
            type=int
        )

        recipe = RecipeManager.get_recipe(
            recipe_code
        )

        if not recipe:

            flash(
                "Recipe not found.",
                "error"
            )

            return redirect("/recipes")

        if not selected_version:

            selected_version = recipe[
                "current_version"
            ]

        if _is_legacy_historical_version(
            recipe,
            selected_version
        ):

            flash(
                (
                    "Historical recipe versions are locked. "
                    "Open the current production version for changes."
                ),
                "error"
            )

            return redirect(
                f"/recipes/{recipe_code}/parameters?version={selected_version}"
            )

        parameter = RecipeManager.get_parameter(
            recipe_code,
            parameter_name
        )

        if request.method == "POST":

            new_value = request.form.get(
                "parameter_value"
            )

            try:

                RecipeManager.update_parameter(

                    recipe_code=recipe_code,

                    version=selected_version,

                    parameter_name=parameter_name,

                    new_value=new_value,

                    username=session["username"]

                )

                flash(
                    f"{parameter_name} Updated",
                    "success"
                )

                return redirect(
                    f"/recipes/{recipe_code}/parameters?version={selected_version}"
                )

            except ValueError as error:

                flash(
                    str(error),
                    "error"
                )

        return render_template(

            "recipes/edit_parameter_value.html",

            recipe_code=recipe_code,

            parameter=parameter,

            selected_version=selected_version

        )

    @app.route(
        "/recipes/<recipe_code>/parameters/<parameter_name>/metadata",
        methods=["GET", "POST"]
    )
    def edit_parameter_metadata(
        recipe_code,
        parameter_name
    ):

        if not session.get("logged_in"):
            return redirect("/login")

        if not _engineering_config_allowed():
            return redirect("/recipes")

        selected_version = request.args.get(
            "version",
            type=int
        )

        recipe = RecipeManager.get_recipe(
            recipe_code
        )

        if not recipe:

            flash(
                "Recipe not found.",
                "error"
            )

            return redirect("/recipes")

        if not selected_version:

            selected_version = recipe[
                "current_version"
            ]

        if _is_legacy_historical_version(
            recipe,
            selected_version
        ):

            flash(
                (
                    "Historical recipe metadata is locked. "
                    "Open the current production version for changes."
                ),
                "error"
            )

            return redirect(
                f"/recipes/{recipe_code}/parameters?version={selected_version}"
            )

        parameter = RecipeManager.get_parameter(
            recipe_code,
            parameter_name
        )

        units = RecipeManager.get_active_engineering_units()

        if request.method == "POST":

            min_value = request.form.get(
                "min_value"
            )

            max_value = request.form.get(
                "max_value"
            )

            unit = request.form.get(
                "unit"
            )

            RecipeManager.update_parameter_metadata(

                recipe_code=recipe_code,

                version=selected_version,

                parameter_name=parameter_name,

                min_value=min_value,

                max_value=max_value,

                unit=unit,

                username=session["username"]

            )

            flash(
                f"{parameter_name} Metadata Updated",
                "success"
            )

            return redirect(
                f"/recipes/{recipe_code}/parameters?version={selected_version}"
            )

        return render_template(

            "recipes/edit_parameter_metadata.html",

            recipe_code=recipe_code,

            parameter=parameter,

            selected_version=selected_version,

            units=units

        )

    @app.route(
        "/recipes/<int:recipe_id>/phase-control",
        methods=["GET", "POST"]
    )
    def recipe_phase_control(

        recipe_id

    ):

        if not session.get(
            "logged_in"
        ):

            return redirect(
                "/login"
            )

        from database.recipe_phase_control_manager import (
            RecipePhaseControlManager
        )

        from database.phase_control_manager import (
            PhaseControlManager
        )

        from database.phase_control_default_manager import (
            PhaseControlDefaultManager
        )

        recipe = RecipeManager.get_recipe_by_id(

            recipe_id

        )

        if not recipe:

            flash(
                "Recipe Not Found",
                "error"
            )

            return redirect(
                "/recipes"
            )

        can_edit_phase_control = (
            not _is_historical_recipe(
                recipe
            )
            and
            role_can(
                session.get("role"),
                "recipe_edit"
            )
        )

        edit_mode = can_edit_phase_control

        PhaseControlDefaultManager.initialize_for_stage(
            recipe["stage_id"],
            recipe["stage_type"],
        )

        RecipePhaseControlManager.ensure_group_empty_phase_slots(
            recipe_id=recipe_id,
            stage_type=recipe["stage_type"],
            stage_id=recipe["stage_id"],
            min_slots=12 if (
                str(recipe["stage_type"] or "").upper().replace(" ", "_")
                in {"FIRST_STAGE", "FIRSTSTAGE", "FS"}
            ) else 6
        )

        phase_controls = (

            PhaseControlManager
            .get_phase_controls_by_stage(

                recipe["stage_type"],

                recipe.get("stage_id")

            )

        )

        phase_controls_by_group = {}

        for phase in phase_controls:

            group_code = (
                phase.get("phase_group_code")
                or "MAIN"
            )

            if group_code not in phase_controls_by_group:

                phase_controls_by_group[group_code] = []

            phase_controls_by_group[group_code].append(
                phase
            )

        if request.method == "POST":

            if not can_edit_phase_control:

                flash(
                    (
                        "Historical released recipe phase controls are "
                        "locked. Open the current production version."
                    ),
                    "error"
                )

                return redirect(
                    f"/recipes/{recipe_id}/phase-control"
                )

            phase_rows = (

                RecipePhaseControlManager
                .get_recipe_phase_control(

                    recipe_id

                )

            )

            empty_phase = next(

                (
                    phase
                    for phase in phase_controls

                    if (
                        phase[
                            "phase_control_name"
                        ]
                        or
                        ""
                    ).strip().upper() == "EMPTY PHASE"
                ),

                None

            )

            empty_phase_id = None

            if empty_phase:

                empty_phase_id = empty_phase["id"]

            for row in phase_rows:

                phase_control_id = request.form.get(

                    f"phase_control_id_{row['id']}"

                )

                if (

                    not phase_control_id

                    and

                    empty_phase_id

                ):

                    phase_control_id = (
                        empty_phase_id
                    )

                row_group_code = (
                    row.get("phase_group_code")
                    or "MAIN"
                )

                allowed_phases = phase_controls_by_group.get(
                    row_group_code,
                    phase_controls
                )

                allowed_phase_ids = {
                    str(phase["id"])
                    for phase in allowed_phases
                }

                if (
                    phase_control_id
                    and
                    str(phase_control_id) not in allowed_phase_ids
                ):

                    flash(
                        (
                            "Selected phase is not allowed for this "
                            f"{row.get('phase_group_name') or 'phase group'}."
                        ),
                        "error"
                    )

                    return redirect(
                        f"/recipes/{recipe_id}/phase-control"
                    )

                stop_option = request.form.get(

                    f"stop_option_{row['id']}"

                )

                position_option = request.form.get(

                    f"position_option_{row['id']}"

                )

                RecipePhaseControlManager.update_phase_row(

                    phase_row_id=row["id"],

                    phase_control_id=phase_control_id,

                    stop_option=stop_option,

                    position_option=position_option,

                    sequence_no=row["line_no"]

                )

            flash(

                "Phase Control Saved",

                "success"

            )

            return redirect(

                f"/recipes/{recipe_id}/phase-control"

            )

        phase_rows = (

            RecipePhaseControlManager
            .get_recipe_phase_control(

                recipe_id

            )

        )

        phase_groups = []

        phase_group_map = {}

        for row in phase_rows:

            group_code = (
                row.get("phase_group_code")
                or "MAIN"
            )

            if group_code not in phase_group_map:

                phase_group_map[group_code] = {
                    "code": group_code,
                    "name": (
                        row.get("phase_group_name")
                        or "Phase Control"
                    ),
                    "rows": [],
                    "options": phase_controls_by_group.get(
                        group_code,
                        phase_controls
                    )
                }

                phase_groups.append(
                    phase_group_map[group_code]
                )

            phase_group_map[group_code]["rows"].append(
                row
            )

        return render_template(

            "recipes/recipe_phase_control.html",

            recipe=recipe,

            phase_rows=phase_rows,

            phase_controls=phase_controls,

            phase_controls_by_group=phase_controls_by_group,

            phase_groups=phase_groups,

            can_edit_phase_control=can_edit_phase_control,

            edit_mode=edit_mode

        )

    @app.route(
        "/recipes/<recipe_code>/parameters/<parameter_name>/history"
    )
    def parameter_history(
        recipe_code,
        parameter_name
    ):

        if not session.get("logged_in"):
            return redirect("/login")

        history = AuditManager.get_parameter_history(

            recipe_code,

            parameter_name

        )

        for row in history:

            row["display_time"] = utc_to_ist(
                row["timestamp"]
            )

        return render_template(

            "recipes/parameter_history.html",

            recipe_code=recipe_code,

            parameter_name=parameter_name,

            history=history

        )
    
    @app.route(
        "/recipes/<recipe_code>/compare",
        methods=["GET", "POST"]
    )
    def compare_recipe_versions(
        recipe_code
    ):

        if not session.get("logged_in"):
            return redirect("/login")

        versions = RecipeManager.get_recipe_versions(
            recipe_code
        )

        comparison = None

        if request.method == "POST":

            version_a = int(
                request.form.get(
                    "version_a"
                )
            )

            version_b = int(
                request.form.get(
                    "version_b"
                )
            )

            comparison = RecipeManager.compare_versions(

                recipe_code=recipe_code,

                version_a=version_a,

                version_b=version_b

            )

        return render_template(

            "recipes/compare_versions.html",

            recipe_code=recipe_code,

            versions=versions,

            comparison=comparison

        )
    
    @app.route("/engineering-units")
    def engineering_units():

        if not session.get("logged_in"):
            return redirect("/login")

        if not _engineering_config_allowed():
            return redirect("/recipes")

        units = RecipeManager.get_all_engineering_units()

        return render_template(

            "admin/engineering_units.html",

            units=units

        )
    
    @app.route(
        "/engineering-units/create",
        methods=["GET", "POST"]
    )
    def create_engineering_unit():

        if not session.get("logged_in"):
            return redirect("/login")

        if not _engineering_config_allowed():
            return redirect("/recipes")

        if request.method == "POST":

            unit_code = request.form.get(
                "unit_code"
            )

            description = request.form.get(
                "description"
            )

            RecipeManager.add_engineering_unit(

                unit_code,

                description

            )

            AuditManager.log_event(

                username=session["username"],

                role=session["role"],

                action="ENGINEERING_UNIT_CREATED",

                new_value=unit_code

            )

            flash(
                f"Unit {unit_code} Created",
                "success"
            )

            return redirect(
                "/engineering-units"
            )

        return render_template(
            "admin/create_engineering_unit.html"
        )
    
    @app.route(
        "/engineering-units/<int:unit_id>/edit",
        methods=["GET", "POST"]
    )
    def edit_engineering_unit(
        unit_id
    ):

        if not session.get("logged_in"):
            return redirect("/login")

        if not _engineering_config_allowed():
            return redirect("/recipes")

        unit = RecipeManager.get_engineering_unit(
            unit_id
        )

        if request.method == "POST":

            old_description = unit[
                "description"
            ]

            new_description = request.form.get(
                "description"
            )

            RecipeManager.update_engineering_unit(

                unit_id,

                new_description

            )

            AuditManager.log_event(

                username=session["username"],

                role=session["role"],

                action="ENGINEERING_UNIT_UPDATED",

                record_id=unit_id,

                old_value=old_description,

                new_value=new_description

            )

            flash(
                "Engineering Unit Updated",
                "success"
            )

            return redirect(
                "/engineering-units"
            )

        return render_template(

            "admin/edit_engineering_unit.html",

            unit=unit

        )
    
    @app.route(
        "/engineering-units/<int:unit_id>/disable"
    )
    def disable_engineering_unit(
        unit_id
    ):

        if not session.get("logged_in"):
            return redirect("/login")

        if not _engineering_config_allowed():
            return redirect("/recipes")

        RecipeManager.disable_engineering_unit(
            unit_id
        )

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="ENGINEERING_UNIT_DISABLED",

            record_id=unit_id

        )

        flash(
            "Unit Disabled",
            "success"
        )

        return redirect(
            "/engineering-units"
        )
    
    @app.route(
        "/engineering-units/<int:unit_id>/enable"
    )
    def enable_engineering_unit(
        unit_id
    ):

        if not session.get("logged_in"):
            return redirect("/login")

        if not _engineering_config_allowed():
            return redirect("/recipes")

        RecipeManager.enable_engineering_unit(
            unit_id
        )

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="ENGINEERING_UNIT_ENABLED",

            record_id=unit_id

        )

        flash(
            "Unit Enabled",
            "success"
        )

        return redirect(
            "/engineering-units"
        )
        
    @app.route(
        "/recipes/<machine_code>/<stage_path>"
    )
    def recipe_list_named(machine_code, stage_path):

        if not session.get("logged_in"):
            return redirect("/login")

        ctx = _resolve_machine_stage_by_code(machine_code, stage_path)
        if not ctx:
            flash("Machine/stage not found. Select machine and stage before opening recipes.", "error")
            return redirect("/recipes")

        canonical_url = _friendly_recipe_list_url(ctx)
        current_path = f"/recipes/{machine_code}/{stage_path}"
        if current_path != canonical_url:
            return redirect(canonical_url)

        recipes = RecipeManager.get_recipes(ctx["machine_id"], ctx["stage_id"])
        return _render_recipe_list_page(ctx=ctx, recipes=recipes)

    @app.route(
        "/recipes/<int:machine_id>/<int:stage_id>"
    )
    def recipe_list(machine_id, stage_id):

        if not session.get("logged_in"):
            return redirect("/login")

        ctx = _resolve_machine_stage_by_id(machine_id, stage_id)
        if ctx:
            return redirect(_friendly_recipe_list_url(ctx))

        flash("Machine/stage not found or inactive.", "error")
        return redirect("/recipes")

    @app.route(
        "/recipes/<int:recipe_id>/copy",
        methods=["GET", "POST"]
    )
    def copy_recipe(
        recipe_id
    ):

        if not session.get(
            "logged_in"
        ):
            return redirect(
                "/login"
            )

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            flash(
                "Recipe Not Found",
                "error"
            )

            return redirect(
                "/recipes"
            )

        if not role_can(
            session.get("role"),
            "recipe_copy"
        ):

            flash(
                "Your role cannot copy recipes.",
                "error"
            )

            return redirect(
                f"/recipe-editor/{recipe_id}"
            )

        if request.method == "POST":

            new_recipe_code = (
                request.form.get(
                    "recipe_code"
                )
            )

            new_recipe_name = (
                request.form.get(
                    "recipe_name"
                )
            )

            success, result = (
                RecipeManager
                .copy_recipe(

                    source_recipe_id=
                    recipe_id,

                    new_recipe_code=
                    new_recipe_code,

                    new_recipe_name=
                    new_recipe_name,

                    username=
                    session["username"]

                )
            )

            if success:

                flash(
                    f"Recipe Copied : {new_recipe_code}",
                    "success"
                )

                return redirect(
                    machine_stage_url("/recipes", context=recipe)
                )

            flash(
                result,
                "error"
            )

        return render_template(

            "recipes/copy_recipe.html",

            recipe=recipe

        )
