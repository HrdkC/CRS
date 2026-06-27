from flask import render_template, request, redirect, session, flash

from database.plc_1d_array_recipe_builder import PLC1DArrayRecipeBuilder
from flask_app.security.role_guard import role_can


def _engineering_config_allowed():
    return (
        session.get("logged_in")
        and role_can(session.get("role"), "engineering_config")
    )


def register_plc_array_import_routes(app):

    @app.route("/plc-array-import/plc/<int:plc_id>")
    def plc_array_import_by_plc(plc_id):
        if not _engineering_config_allowed():
            return redirect("/")

        context = PLC1DArrayRecipeBuilder.get_machine_stage_context_by_plc_id(plc_id)
        if not context:
            flash("PLC not found or PLC is not linked to any machine/stage.", "error")
            return redirect("/plcs")

        return redirect(f"/plc-array-import/{context['machine_id']}/{context['stage_id']}")

    @app.route(
        "/plc-array-import/<int:machine_id>/<int:stage_id>",
        methods=["GET", "POST"],
    )
    def plc_array_import(machine_id, stage_id):
        if not _engineering_config_allowed():
            return redirect("/")

        context = PLC1DArrayRecipeBuilder.get_machine_stage_context(
            machine_id=machine_id,
            stage_id=stage_id,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/machines")

        active_plc = PLC1DArrayRecipeBuilder.get_active_plc(
            machine_id=machine_id,
            stage_id=stage_id,
        )

        existing_parameter_count = PLC1DArrayRecipeBuilder.count_parameter_definitions(
            machine_id=machine_id,
            stage_id=stage_id,
        )
        existing_recipe_count = PLC1DArrayRecipeBuilder.count_stage_recipes(
            machine_id=machine_id,
            stage_id=stage_id,
        )

        default_recipe_code = "GT_P15_SS_TEST_001"
        default_recipe_name = "P15 Second Stage Test Recipe 001"
        if context.get("stage_type") != "SECOND_STAGE":
            default_recipe_code = f"GT_{context.get('machine_code', 'PLC')}_{context.get('stage_type', 'STAGE')}_PLC_IMPORT_001"
            default_recipe_name = f"{context.get('machine_code', 'PLC')} {context.get('stage_type', 'Stage')} PLC Import Test 001"

        form_data = {
            "tag_name": request.values.get("tag_name", "").strip(),
            "start_index": request.values.get("start_index", "0").strip(),
            "end_index": request.values.get("end_index", "119").strip(),
            "recipe_code": request.values.get("recipe_code", default_recipe_code).strip(),
            "recipe_name": request.values.get("recipe_name", default_recipe_name).strip(),
            "version": request.values.get("version", "1").strip(),
            "unit": request.values.get("unit", "").strip(),
            "min_value": request.values.get("min_value", "0").strip(),
            "max_value": request.values.get("max_value", "999999").strip(),
            "datatype": request.values.get("datatype", "REAL").strip().upper(),
            "reason": request.values.get("reason", "").strip(),
        }

        result = None

        if request.method == "POST":
            action = request.form.get("action", "preview")
            dry_run = action != "build"

            result = PLC1DArrayRecipeBuilder.build_from_plc_array(
                machine_id=machine_id,
                stage_id=stage_id,
                tag_name=form_data["tag_name"],
                start_index=form_data["start_index"],
                end_index=form_data["end_index"],
                recipe_code=form_data["recipe_code"],
                recipe_name=form_data["recipe_name"],
                version=form_data["version"],
                username=session.get("username", "system"),
                role=session.get("role", "SYSTEM"),
                reason=form_data["reason"],
                unit=form_data["unit"],
                min_value=form_data["min_value"],
                max_value=form_data["max_value"],
                datatype=form_data["datatype"],
                dry_run=dry_run,
            )

            if result.get("created") and result.get("recipe_id"):
                flash(
                    "Draft recipe created from PLC 1D array. Rename parameters and set limits before release.",
                    "success",
                )
                return redirect(f"/recipe-editor/{result['recipe_id']}")

            for error in result.get("errors", []):
                flash(error, "error")
            for warning in result.get("warnings", []):
                flash(warning, "warning")

        return render_template(
            "plc_array_import/import_1d_array.html",
            context=context,
            active_plc=active_plc,
            existing_parameter_count=existing_parameter_count,
            existing_recipe_count=existing_recipe_count,
            form_data=form_data,
            result=result,
        )
