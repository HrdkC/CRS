from flask import render_template, request, redirect, session, flash

from database.plc_1d_array_recipe_builder import PLC1DArrayRecipeBuilder
from flask_app.security.role_guard import role_can
from flask_app.stage_url_helper import (
    get_machine_stage_context_by_code,
    get_machine_stage_context_by_id,
    machine_stage_url,
    add_machine_stage_url_fields,
)


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

        return redirect(machine_stage_url("/plc-array-import", context=context))

    @app.route(
        "/plc-array-import/<machine_code>/<stage_code>",
        methods=["GET", "POST"],
    )
    def plc_array_import_named(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(machine_code, stage_code)
        if not context:
            flash("Machine/stage not found. Use friendly route like /plc-array-import/P15/FS or /plc-array-import/P15/SS.", "error")
            return redirect("/machines")

        if request.method == "GET":
            canonical_url = machine_stage_url(
                "/plc-array-import",
                context=context,
                query=request.args
            )
            current_path = f"/plc-array-import/{machine_code}/{stage_code}"
            if current_path != canonical_url.split("?")[0]:
                return redirect(canonical_url)

        return _render_plc_array_import(context)

    @app.route(
        "/plc-array-import/<int:machine_id>/<int:stage_id>",
        methods=["GET", "POST"],
    )
    def plc_array_import(machine_id, stage_id):
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

        if request.method == "GET":
            return redirect(
                machine_stage_url(
                    "/plc-array-import",
                    context=context,
                    query=request.args
                )
            )

        return _render_plc_array_import(context)



def _default_import_values(context):
    """Return safe PLC 1D array import defaults for the selected machine/stage."""
    machine_code = str(context.get("machine_code") or "PLC").upper()
    stage_type = str(context.get("stage_type") or "STAGE").upper()
    stage_code = str(context.get("stage_url_code") or "").upper()

    default_end_index = "119"
    default_recipe_code = f"GT_{machine_code}_{stage_code or stage_type}_PLC_IMPORT_001"
    default_recipe_name = f"{machine_code} {stage_code or stage_type} PLC Import Test 001"

    if machine_code == "P15" and stage_type == "SECOND_STAGE":
        default_end_index = "149"
        default_recipe_code = "GT_P15_SS_TEST_001"
        default_recipe_name = "P15 Second Stage Test Recipe 001"
    elif machine_code == "P15" and stage_type == "FIRST_STAGE":
        default_recipe_code = "GT_P15_FS_TEST_001"
        default_recipe_name = "P15 First Stage Test Recipe 001"

    return {
        "tag_name": "CRS_Recipe_Data",
        "start_index": "0",
        "end_index": default_end_index,
        "recipe_code": default_recipe_code,
        "recipe_name": default_recipe_name,
        "version": "1",
        "unit": "",
        "min_value": "0",
        "max_value": "999999",
        "datatype": "REAL",
        "reason": "",
    }


def _empty_preview_result(form_data, error_message):
    return {
        "ok": False,
        "plc": None,
        "tag_name": form_data.get("tag_name", ""),
        "start_index": form_data.get("start_index", ""),
        "end_index": form_data.get("end_index", ""),
        "count": 0,
        "values": [],
        "errors": [error_message],
        "warnings": [],
        "dry_run": True,
        "created": False,
        "recipe_id": None,
        "parameter_count": 0,
        "phase_count": 0,
    }

def _render_plc_array_import(context):
        machine_id = context["machine_id"]
        stage_id = context["stage_id"]
        add_machine_stage_url_fields(context)

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

        defaults = _default_import_values(context)
        form_data = {
            "tag_name": request.values.get("tag_name", defaults["tag_name"]).strip(),
            "start_index": request.values.get("start_index", defaults["start_index"]).strip(),
            "end_index": request.values.get("end_index", defaults["end_index"]).strip(),
            "recipe_code": request.values.get("recipe_code", defaults["recipe_code"]).strip(),
            "recipe_name": request.values.get("recipe_name", defaults["recipe_name"]).strip(),
            "version": request.values.get("version", defaults["version"]).strip(),
            "unit": request.values.get("unit", defaults["unit"]).strip(),
            "min_value": request.values.get("min_value", defaults["min_value"]).strip(),
            "max_value": request.values.get("max_value", defaults["max_value"]).strip(),
            "datatype": request.values.get("datatype", defaults["datatype"]).strip().upper(),
            "reason": request.values.get("reason", defaults["reason"]).strip(),
        }
        standard_array_tags = ["CRS_Recipe_Data", "CRS_Test_Recipe_Data"]

        result = None

        if request.method == "POST":
            action = request.form.get("action", "preview")
            dry_run = action != "build"

            try:
                if dry_run:
                    # Preview must be a pure PLC read only.
                    # Do not enter build/import validation path until user clicks Build.
                    # This uses the same fresh LogixDriver read method as the diagnostic script.
                    result = PLC1DArrayRecipeBuilder.read_array_values(
                        machine_id=machine_id,
                        stage_id=stage_id,
                        tag_name=form_data["tag_name"],
                        start_index=form_data["start_index"],
                        end_index=form_data["end_index"],
                    )
                    result.update({
                        "dry_run": True,
                        "created": False,
                        "recipe_id": None,
                        "parameter_count": len(result.get("values", [])) if result.get("ok") else 0,
                        "phase_count": 0,
                    })
                    if result.get("ok"):
                        result.setdefault("warnings", []).append(
                            "Preview only. No database rows were created and no PLC values were written."
                        )
                        if existing_parameter_count > 0:
                            result.setdefault("warnings", []).append(
                                "Parameter master already exists for this machine/stage. Preview is allowed, but Build will not overwrite existing parameter definitions."
                            )
                else:
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
                        dry_run=False,
                    )
            except Exception as ex:
                result = _empty_preview_result(
                    form_data,
                    f"PLC array preview/build failed before completion: {ex}",
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
            plc_tag_browser_url=machine_stage_url("/plc-tags", context=context),
            plc_array_import_url=machine_stage_url("/plc-array-import", context=context),
            existing_parameter_count=existing_parameter_count,
            existing_recipe_count=existing_recipe_count,
            form_data=form_data,
            result=result,
            standard_array_tags=standard_array_tags,
        )
