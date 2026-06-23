from flask import render_template, session, redirect, request, flash

from database.recipe_manager import RecipeManager

from database.audit_manager import AuditManager

from helper.datetime_helper import (
    utc_to_ist
)

from flask_app.security.role_guard import (
    role_can
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


def register_recipe_routes(app):

    @app.route("/recipes")
    def recipes():

        if not session.get("logged_in"):
            return redirect("/login")

        recipes = RecipeManager.list_recipes()

        return render_template(
            "recipes/recipes.html",
            recipes=recipes
        )

    @app.route(
        "/recipes/create/<int:machine_id>/<int:stage_id>",
        methods=["GET", "POST"]
    )
    def create_recipe(

        machine_id,

        stage_id

    ):

        if not session.get("logged_in"):
            return redirect("/login")

        if not role_can(
            session.get("role"),
            "recipe_edit"
        ):

            flash(
                "Your role cannot create recipes.",
                "error"
            )

            return redirect(
                f"/recipes/{machine_id}/{stage_id}"
            )

        if request.method == "POST":

            recipe_code = request.form.get(
                "recipe_code"
            )

            recipe_name = request.form.get(
                "recipe_name"
            )

            RecipeManager.create_recipe(

                machine_id=machine_id,

                stage_id=stage_id,

                recipe_code=recipe_code,

                recipe_name=recipe_name,

                created_by=session["username"]

            )

            flash(
                f"Recipe Created : {recipe_code}",
                "success"
            )

            return redirect(
                f"/recipes/{machine_id}/{stage_id}"
            )

        return render_template(

            "recipes/create_recipe.html",

            machine_id=machine_id,

            stage_id=stage_id

        )

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

        if session["role"] != "ADMIN":
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

        phase_controls = (

            PhaseControlManager
            .get_phase_controls_by_stage(

                "FIRST_STAGE"

            )

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

                    if phase[
                        "phase_control_name"
                    ] == "Empty Phase"
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

        return render_template(

            "recipes/recipe_phase_control.html",

            recipe=recipe,

            phase_rows=phase_rows,

            phase_controls=phase_controls,

            can_edit_phase_control=can_edit_phase_control

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

        if session["role"] != "ADMIN":
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

        if session["role"] != "ADMIN":
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

        if session["role"] != "ADMIN":
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

        if session["role"] != "ADMIN":
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

        if session["role"] != "ADMIN":
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
        "/recipes/<int:machine_id>/<int:stage_id>"
    )
    def recipe_list(

        machine_id,

        stage_id

    ):

        if not session.get(
            "logged_in"
        ):
            return redirect(
                "/login"
            )

        recipes = (

            RecipeManager
            .get_recipes(

                machine_id,

                stage_id

            )

        )

        return render_template(

            "recipes/recipes.html",

            recipes=recipes,

            machine_id=machine_id,

            stage_id=stage_id

        )
        
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
                    f"/recipes/{recipe['machine_id']}/{recipe['stage_id']}"
                )

            flash(
                result,
                "error"
            )

        return render_template(

            "recipes/copy_recipe.html",

            recipe=recipe

        )
