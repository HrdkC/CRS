from flask import (
    render_template,
    request,
    redirect,
    session,
    flash,
    jsonify
)

import threading

from urllib.parse import (
    urlencode
)

from database.recipe_manager import (
    RecipeManager
)

from database.recipe_parameter_value_manager import (
    RecipeParameterValueManager
)

from database.recipe_parameter_audit_manager import (
    RecipeParameterAuditManager
)

from database.parameter_definition_manager import (
    ParameterDefinitionManager
)

from database.audit_manager import (
    AuditManager
)

from database.recipe_version_manager import (
    RecipeVersionManager
)

from database.recipe_phase_control_manager import (
    RecipePhaseControlManager
)

from helper.datetime_helper import (
    utc_to_ist
)

from database.recipe_approval_manager import (
    RecipeApprovalManager
)

from database.recipe_status_history_manager import (
    RecipeStatusHistoryManager
)

from database.recipe_download_eligibility_manager import (
    RecipeDownloadEligibilityManager
)

from database.plc_download_preparation_manager import (
    PLCDownloadPreparationManager
)

from database.plc_buffer_operation_manager import (
    PLCBufferOperationManager
)

from database.plc_operation_job_manager import (
    PLCOperationJobManager
)

from database.recipe_resource_lock_manager import (
    RecipeResourceLockManager
)

from flask_app.security.role_guard import (
    role_can
)


def _buffer_operation_capability(operation):

    if operation in [
        "recipe_save",
        "upload_from_plc"
    ]:

        return "recipe_edit"

    return "recipe_download"




def _lock_context():
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = (forwarded_for.split(",")[0].strip() if forwarded_for else request.remote_addr)
    return {
        "username": session.get("username"),
        "user_role": session.get("role"),
        "session_id": session.get("session_id"),
        "workstation_name": (
            request.headers.get("X-Workstation-Name")
            or request.headers.get("X-Client-Workstation")
            or request.headers.get("X-Forwarded-Host")
            or request.host
        ),
        "client_ip": client_ip,
        "user_agent": request.headers.get("User-Agent", ""),
    }


def _lock_belongs_to_current_user(lock_row):
    return RecipeResourceLockManager.active_lock_belongs_to(
        lock_row,
        username=session.get("username"),
        session_id=session.get("session_id")
    )


def _format_lock_owner(lock_row):
    if not lock_row:
        return "another user"
    return (
        f"{lock_row.get('locked_by') or 'another user'} "
        f"({lock_row.get('operation_type') or 'operation'})"
    )


def _active_recipe_operation_lock(recipe_id):
    lock_row = RecipeResourceLockManager.get_active_lock(
        "RECIPE_OPERATION",
        recipe_id
    )
    if lock_row and not _lock_belongs_to_current_user(lock_row):
        return lock_row
    return None


def _active_plc_operation_lock(plc_id):
    lock_row = RecipeResourceLockManager.get_active_lock(
        "PLC_OPERATION",
        plc_id
    )
    if lock_row and not _lock_belongs_to_current_user(lock_row):
        return lock_row
    return None


def _acquire_recipe_edit_lock(recipe_id):
    ctx = _lock_context()
    return RecipeResourceLockManager.acquire_lock(
        resource_type="RECIPE_EDIT",
        resource_id=recipe_id,
        operation_type="PARAMETER_EDIT",
        username=ctx["username"],
        user_role=ctx["user_role"],
        session_id=ctx["session_id"],
        workstation_name=ctx["workstation_name"],
        client_ip=ctx["client_ip"],
        user_agent=ctx["user_agent"],
        ttl_minutes=15,
        notes="Recipe parameter edit lock"
    )

def _deny(message, redirect_url="/"):

    flash(
        message,
        "error"
    )

    return redirect(
        redirect_url
    )


def _get_parameter_group(

    row

):

    name = (
        row.get(
            "parameter_name"
        )
        or
        ""
    ).upper()

    unit = (
        row.get(
            "unit"
        )
        or
        ""
    ).upper()

    if (
        "ANGLE" in name
        or
        unit == "DEG"
    ):

        return "Angle"

    if "WIDTH" in name:

        return "Width"

    if (
        "LENGTH" in name
        or
        unit in [
            "MM",
            "CM",
            "M"
        ]
    ):

        return "Length"

    if (
        "SPEED" in name
        or
        unit in [
            "RPM",
            "MPM",
            "M/MIN"
        ]
    ):

        return "Speed"

    if (
        "PRESS" in name
        or
        unit in [
            "BAR",
            "PSI",
            "KG/CM2"
        ]
    ):

        return "Pressure"

    if (
        "TIME" in name
        or
        "DELAY" in name
        or
        unit in [
            "SEC",
            "S",
            "MS"
        ]
    ):

        return "Time"

    return "Other"


def _build_recipe_editor_metrics(

    rows

):

    metrics = {

        "total": len(
            rows
        ),

        "modified": 0,

        "out_of_range": 0,

        "below_range": 0,

        "above_range": 0,

        "zero_values": 0,

        "groups": {},

        "units": {}

    }

    for row in rows:

        value = row.get(
            "parameter_value"
        )

        min_value = row.get(
            "min_value"
        )

        max_value = row.get(
            "max_value"
        )

        if row.get(
            "is_modified"
        ):

            metrics["modified"] += 1

        if value == 0:

            metrics["zero_values"] += 1

        if (
            value is not None
            and
            min_value is not None
            and
            value < min_value
        ):

            metrics["out_of_range"] += 1

            metrics["below_range"] += 1

        elif (
            value is not None
            and
            max_value is not None
            and
            value > max_value
        ):

            metrics["out_of_range"] += 1

            metrics["above_range"] += 1

        group_name = _get_parameter_group(
            row
        )

        if group_name not in metrics["groups"]:

            metrics["groups"][group_name] = {

                "name": group_name,

                "count": 0,

                "modified": 0,

                "out_of_range": 0

            }

        metrics["groups"][group_name]["count"] += 1

        if row.get(
            "is_modified"
        ):

            metrics["groups"][group_name]["modified"] += 1

        if (
            value is not None
            and
            min_value is not None
            and
            value < min_value
        ) or (
            value is not None
            and
            max_value is not None
            and
            value > max_value
        ):

            metrics["groups"][group_name]["out_of_range"] += 1

        unit_name = (
            row.get(
                "unit"
            )
            or
            "-"
        )

        metrics["units"][unit_name] = (
            metrics["units"].get(
                unit_name,
                0
            )
            + 1
        )

    total = metrics["total"] or 1

    metrics["modified_percent"] = round(
        (
            metrics["modified"]
            /
            total
        )
        * 100
    )

    metrics["valid_percent"] = round(
        (
            (
                metrics["total"]
                -
                metrics["out_of_range"]
            )
            /
            total
        )
        * 100
    )

    metrics["groups"] = sorted(
        metrics["groups"].values(),
        key=lambda item: (
            item["out_of_range"],
            item["modified"],
            item["count"]
        ),
        reverse=True
    )

    metrics["units"] = sorted(
        [
            {
                "name": key,
                "count": value
            }
            for key, value in metrics["units"].items()
        ],
        key=lambda item: item["count"],
        reverse=True
    )

    return metrics


def _build_phase_groups_for_display(phase_rows):

    phase_groups = []

    phase_group_map = {}

    for row in phase_rows:

        group_code = (
            row.get("phase_group_code")
            or
            "MAIN"
        )

        if group_code not in phase_group_map:

            phase_group_map[group_code] = {
                "code": group_code,
                "name": (
                    row.get("phase_group_name")
                    or
                    "Phase Control"
                ),
                "rows": []
            }

            phase_groups.append(
                phase_group_map[group_code]
            )

        phase_group_map[group_code]["rows"].append(row)

    return phase_groups


def _optional_float(value):

    value = str(
        value
        if value is not None
        else
        ""
    ).strip()

    if value == "":

        return None

    return float(value)


def _optional_int(value):

    value = str(
        value
        if value is not None
        else
        ""
    ).strip()

    if value == "":

        return None

    return int(value)


def _is_current_released_recipe(

    recipe

):

    return (
        recipe
        and
        recipe.get(
            "status"
        )
        ==
        "RELEASED"
        and
        recipe.get(
            "version_usage_status"
        )
        ==
        "CURRENT_RELEASED"
    )

def register_recipe_editor_routes(app):

    @app.route(
        "/recipe-editor/<int:recipe_id>"
    )
    def recipe_editor(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        recipe = (

            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )

        )

        search_text = request.args.get(
            "search",
            ""
        )

        modified_only = request.args.get(
            "modified_only",
            "0"
        )

        jump_tag = request.args.get(
            "jump_tag",
            ""
        )

        try:

            page = int(
                request.args.get(
                    "page",
                    1
                )
            )

        except Exception:

            page = 1

        try:

            page_size = int(
                request.args.get(
                    "page_size",
                    50
                )
            )

        except Exception:

            page_size = 50

        if page < 1:

            page = 1

        if page_size not in [
            25,
            50,
            100,
            9999
        ]:

            page_size = 50

        all_values = (
            RecipeParameterValueManager
            .get_recipe_values(
                recipe_id
            )
        )

        editor_metrics = _build_recipe_editor_metrics(
            all_values
        )

        values = list(
            all_values
        )

        if search_text:

            values = [

                row

                for row in values

                if search_text.upper()

                in

                row[
                    "parameter_name"
                ].upper()

            ]

        if modified_only == "1":

            values = [

                row

                for row in values

                if row[
                    "is_modified"
                ] == 1

            ]

        if jump_tag:

            try:

                jump_tag_int = int(
                    jump_tag
                )

                for position, row in enumerate(values):

                    if row[
                        "tag_index"
                    ] >= jump_tag_int:

                        page = (
                            position
                            //
                            page_size
                        ) + 1

                        break

            except:

                pass

        filtered_parameters = len(
            values
        )

        start_index = (
            (page - 1)
            * page_size
        )

        end_index = (
            start_index
            + page_size
        )

        paged_values = values[
            start_index:end_index
        ]

        shown_from = 0

        shown_to = 0

        if paged_values:

            shown_from = start_index + 1

            shown_to = (
                start_index
                +
                len(
                    paged_values
                )
            )

        base_query = {

            "search": search_text,

            "page_size": page_size,

            "modified_only": modified_only,

            "jump_tag": jump_tag

        }

        previous_url = None

        next_url = None

        if page > 1:

            previous_query = dict(
                base_query
            )

            previous_query["page"] = page - 1

            previous_url = (
                "?"
                +
                urlencode(
                    previous_query
                )
            )

        if len(
            paged_values
        ) == page_size and end_index < filtered_parameters:

            next_query = dict(
                base_query
            )

            next_query["page"] = page + 1

            next_url = (
                "?"
                +
                urlencode(
                    next_query
                )
            )

        summary = (
            RecipeParameterAuditManager
            .get_recipe_summary(
                recipe_id
            )
        )
        
        if summary["last_changed_at"] != "-":

            summary["last_changed_at"] = (
                utc_to_ist(
                    summary["last_changed_at"]
                )
            )
        
        phase_control = (
            RecipePhaseControlManager
            .get_recipe_phase_control(
                recipe_id
            )
        )

        phase_groups = _build_phase_groups_for_display(
            phase_control
        )

        production_revision_source = (
            RecipeVersionManager
            .get_previous_released_version(
                recipe_id
            )
        )

        download_eligibility = (
            RecipeDownloadEligibilityManager
            .check_eligibility(
                recipe_id
            )
        )

        can_edit_values = (
            recipe
            and
            (
                recipe["status"] != "RELEASED"
                or
                _is_current_released_recipe(
                    recipe
                )
            )
        )

        user_role = session.get(
            "role"
        )

        can_edit_values = (
            can_edit_values
            and
            role_can(
                user_role,
                "recipe_edit"
            )
        )

        can_submit_review = role_can(
            user_role,
            "recipe_submit_review"
        )

        can_approve_recipe = role_can(
            user_role,
            "recipe_approve"
        )

        can_download_recipe = role_can(
            user_role,
            "recipe_download"
        )

        can_copy_recipe = role_can(
            user_role,
            "recipe_copy"
        )

        active_operation_lock = _active_recipe_operation_lock(recipe_id)
        if active_operation_lock:
            can_edit_values = False
            can_download_recipe = False

        edit_lock_reason = ""

        if active_operation_lock:
            edit_lock_reason = (
                "Recipe is locked by "
                + _format_lock_owner(active_operation_lock)
                + ". Wait until the active operation reaches 100% success/failure."
            )

        if (
            recipe
            and
            recipe["status"] == "RELEASED"
            and
            not _is_current_released_recipe(
                recipe
            )
        ):

            edit_lock_reason = (
                "Historical released versions are locked. "
                "Open the current production version for changes."
            )

        return render_template(

            "recipes/editor.html",

            recipe=recipe,

            values=paged_values,

            summary=summary,
            
            phase_control=phase_control,

            phase_groups=phase_groups,

            production_revision_source=production_revision_source,

            download_eligibility=download_eligibility,

            editor_metrics=editor_metrics,

            can_edit_values=can_edit_values,

            can_submit_review=can_submit_review,

            can_approve_recipe=can_approve_recipe,

            can_download_recipe=can_download_recipe,

            can_copy_recipe=can_copy_recipe,

            edit_lock_reason=edit_lock_reason,

            search_text=search_text,

            modified_only=modified_only,

            jump_tag=jump_tag,

            page=page,

            page_size=page_size,

            total_parameters=filtered_parameters,

            filtered_parameters=filtered_parameters,

            shown_from=shown_from,

            shown_to=shown_to,

            previous_url=previous_url,

            next_url=next_url,

        )

    @app.route(
        "/recipe-editor/<int:recipe_id>/parameters/bulk-edit",
        methods=["GET", "POST"]
    )
    def bulk_edit_recipe_parameters(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            flash(
                "Recipe not found.",
                "error"
            )

            return redirect("/recipes")

        user_role = session.get(
            "role"
        )

        can_edit_values = (
            recipe["status"] != "RELEASED"
            or
            _is_current_released_recipe(
                recipe
            )
        )

        can_edit_values = (
            can_edit_values
            and
            role_can(
                user_role,
                "recipe_edit"
            )
        )

        can_edit_details = role_can(
            user_role,
            "engineering_config"
        )

        if (
            recipe["status"] == "RELEASED"
            and
            not _is_current_released_recipe(
                recipe
            )
        ):

            flash(
                (
                    "Historical released recipe cannot be edited. "
                    "Open the current production version."
                ),
                "error"
            )

            return redirect(
                f"/recipe-editor/{recipe_id}"
            )

        if not can_edit_values:

            return _deny(
                (
                    "Your role can view and download recipes, "
                    "but cannot edit recipe values."
                ),
                f"/recipe-editor/{recipe_id}"
            )

        active_operation_lock = _active_recipe_operation_lock(recipe_id)

        if active_operation_lock:

            flash(
                "Recipe edit is blocked because "
                + _format_lock_owner(active_operation_lock)
                + " is still running. Wait until it reaches 100% success/failure.",
                "warning"
            )

            return redirect(
                f"/recipe-editor/{recipe_id}"
            )

        rows = (
            RecipeParameterValueManager
            .get_recipe_values(
                recipe_id
            )
        )

        search_text = request.args.get(
            "search",
            ""
        )

        if search_text:

            rows = [
                row
                for row in rows
                if (
                    search_text.upper()
                    in
                    str(row.get("parameter_name") or "").upper()
                    or
                    search_text
                    in
                    str(row.get("tag_index") or "")
                    or
                    search_text
                    in
                    str(row.get("plc_array_index") or "")
                )
            ]

        if request.method == "POST":

            all_rows = (
                RecipeParameterValueManager
                .get_recipe_values(
                    recipe_id
                )
            )

            row_by_value_id = {
                str(row["id"]): row
                for row in all_rows
            }

            selected_ids = request.form.getlist(
                "selected_value_id"
            )

            change_reason = (
                request.form.get(
                    "change_reason"
                )
                or
                ""
            ).strip()

            if not change_reason:

                flash(
                    "Enter a change reason before saving selected parameters.",
                    "error"
                )

                return redirect(
                    f"/recipe-editor/{recipe_id}/parameters/bulk-edit"
                )

            if not selected_ids:

                flash(
                    "Select at least one parameter row to save.",
                    "error"
                )

                return redirect(
                    f"/recipe-editor/{recipe_id}/parameters/bulk-edit"
                )

            validation_errors = []

            parsed_changes = {}

            final_names = {}

            final_plc_indexes = {}

            for row in all_rows:

                row_id = str(row["id"])

                selected = row_id in selected_ids

                try:

                    value = float(
                        request.form.get(
                            f"parameter_value_{row_id}",
                            row["parameter_value"]
                        )
                    ) if selected else row["parameter_value"]

                    if selected and can_edit_details:

                        parameter_name = (
                            request.form.get(
                                f"parameter_name_{row_id}",
                                row["parameter_name"]
                            )
                            or
                            ""
                        ).strip()

                        plc_array_index = _optional_int(
                            request.form.get(
                                f"plc_array_index_{row_id}",
                                row.get("plc_array_index")
                            )
                        )

                        unit = (
                            request.form.get(
                                f"unit_{row_id}",
                                row.get("unit") or ""
                            )
                            or
                            ""
                        ).strip()

                        min_value = _optional_float(
                            request.form.get(
                                f"min_value_{row_id}",
                                row.get("min_value")
                            )
                        )

                        max_value = _optional_float(
                            request.form.get(
                                f"max_value_{row_id}",
                                row.get("max_value")
                            )
                        )

                        default_value = _optional_float(
                            request.form.get(
                                f"default_value_{row_id}",
                                row.get("default_value")
                            )
                        )

                    else:

                        parameter_name = row.get("parameter_name") or ""
                        plc_array_index = row.get("plc_array_index")
                        unit = row.get("unit") or ""
                        min_value = row.get("min_value")
                        max_value = row.get("max_value")
                        default_value = row.get("default_value")

                    if selected and not parameter_name:

                        validation_errors.append(
                            f"Tag {row['tag_index']}: parameter name is required."
                        )

                    if (
                        min_value is not None
                        and
                        max_value is not None
                        and
                        float(min_value) > float(max_value)
                    ):

                        validation_errors.append(
                            f"Tag {row['tag_index']}: min value cannot be greater than max value."
                        )

                    if (
                        min_value is not None
                        and
                        float(value) < float(min_value)
                    ):

                        validation_errors.append(
                            f"Tag {row['tag_index']}: value below minimum ({value} < {min_value})."
                        )

                    if (
                        max_value is not None
                        and
                        float(value) > float(max_value)
                    ):

                        validation_errors.append(
                            f"Tag {row['tag_index']}: value above maximum ({value} > {max_value})."
                        )

                    parsed_changes[row_id] = {
                        "row": row,
                        "value": value,
                        "parameter_name": parameter_name,
                        "plc_array_index": plc_array_index,
                        "unit": unit,
                        "min_value": min_value,
                        "max_value": max_value,
                        "default_value": default_value
                    }

                    final_name_key = parameter_name.upper()

                    if final_name_key in final_names:

                        validation_errors.append(
                            f"Duplicate parameter name: {parameter_name}."
                        )

                    final_names[final_name_key] = row["id"]

                    if plc_array_index is not None:

                        if plc_array_index in final_plc_indexes:

                            validation_errors.append(
                                f"Duplicate PLC index: {plc_array_index}."
                            )

                        final_plc_indexes[plc_array_index] = row["id"]

                except Exception as exc:

                    validation_errors.append(
                        f"Tag {row.get('tag_index')}: invalid input ({exc})."
                    )

            unknown_ids = [
                value_id
                for value_id in selected_ids
                if value_id not in row_by_value_id
            ]

            if unknown_ids:

                validation_errors.append(
                    "Selected parameter row does not belong to this recipe."
                )

            if validation_errors:

                flash(
                    "Bulk save blocked: " + validation_errors[0],
                    "error"
                )

                return render_template(
                    "recipes/bulk_edit_parameters.html",
                    recipe=recipe,
                    rows=rows,
                    selected_ids=set(selected_ids),
                    validation_errors=validation_errors[:20],
                    search_text=search_text,
                    can_edit_details=can_edit_details
                )

            edit_lock_result = _acquire_recipe_edit_lock(
                recipe_id
            )

            if not edit_lock_result.get("acquired"):

                active_lock = edit_lock_result.get("active_lock")

                flash(
                    "Recipe is currently being edited by "
                    + _format_lock_owner(active_lock)
                    + ". Please wait until that user saves/closes or the edit lock expires.",
                    "warning"
                )

                return redirect(
                    f"/recipe-editor/{recipe_id}"
                )

            edit_lock_id = (
                edit_lock_result.get("lock")
                or
                {}
            ).get("id")

            changed_count = 0

            detail_changed_count = 0

            try:

                for value_id in selected_ids:

                    parsed = parsed_changes[value_id]

                    row = parsed["row"]

                    if can_edit_details:

                        detail_result = (
                            ParameterDefinitionManager
                            .update_parameter_details(
                                parameter_id=row["parameter_definition_id"],
                                parameter_name=parsed["parameter_name"],
                                plc_array_index=parsed["plc_array_index"],
                                unit=parsed["unit"],
                                min_value=parsed["min_value"],
                                max_value=parsed["max_value"],
                                default_value=parsed["default_value"]
                            )
                        )

                        if detail_result:

                            for field_name, old_value in detail_result["old"].items():

                                new_value = detail_result["new"][field_name]

                                if str(old_value) == str(new_value):

                                    continue

                                detail_changed_count += 1

                                AuditManager.log_event(
                                    username=session.get("username"),
                                    role=user_role,
                                    action="RECIPE_PARAMETER_DETAIL_CHANGED",
                                    change_source="BULK_RECIPE_PARAMETER_EDIT",
                                    recipe_code=recipe["recipe_code"],
                                    recipe_version=recipe["version"],
                                    record_id=row["parameter_definition_id"],
                                    parameter_name=parsed["parameter_name"],
                                    old_value=f"{field_name}: {old_value}",
                                    new_value=f"{field_name}: {new_value}",
                                    reason=change_reason,
                                    client_ip=request.remote_addr,
                                    workstation_name=request.headers.get(
                                        "X-Forwarded-Host",
                                        request.host
                                    )
                                )

                    change_source = "CURRENT_RELEASED_BULK_EDIT"

                    if not _is_current_released_recipe(
                        recipe
                    ):

                        change_source = "DRAFT_RECIPE_BULK_EDIT"

                    value_result = (
                        RecipeParameterValueManager
                        .update_recipe_value(
                            value_id=int(value_id),
                            new_value=parsed["value"],
                            changed_by=session.get("username"),
                            change_reason=change_reason,
                            user_role=user_role,
                            change_source=change_source,
                            client_ip=request.remote_addr,
                            workstation_name=request.headers.get(
                                "X-Forwarded-Host",
                                request.host
                            )
                        )
                    )

                    if value_result.get("changed"):

                        changed_count += 1

                flash(
                    (
                        f"Bulk parameter save completed: {changed_count} value change(s), "
                        f"{detail_changed_count} detail field change(s)."
                    ),
                    "success"
                )

            finally:

                if edit_lock_id:

                    RecipeResourceLockManager.release_lock(
                        edit_lock_id,
                        reason="PARAMETER_BULK_EDIT_COMPLETED"
                    )

            return redirect(
                f"/recipe-editor/{recipe_id}"
            )

        return render_template(
            "recipes/bulk_edit_parameters.html",
            recipe=recipe,
            rows=rows,
            selected_ids=set(),
            validation_errors=[],
            search_text=search_text,
            can_edit_details=can_edit_details
        )

    @app.route(
        "/recipe-editor/edit/<int:value_id>",
        methods=["GET", "POST"]
    )
    def edit_recipe_value(

        value_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        value = (
            RecipeParameterValueManager
            .get_recipe_value_by_id(
                value_id
            )
        )

        if not value:

            flash(
                "Recipe parameter value not found.",
                "error"
            )

            return redirect(
                "/recipes"
            )

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                value["recipe_id"]
            )
        )

        is_current_released_edit = (
            recipe
            and
            _is_current_released_recipe(
                recipe
            )
        )

        if not role_can(
            session.get(
                "role"
            ),
            "recipe_edit"
        ):

            return _deny(
                (
                    "Your role can view and download recipes, "
                    "but cannot edit recipe values."
                ),
                f"/recipe-editor/{value['recipe_id']}"
            )

        if (
            recipe
            and
            recipe["status"] == "RELEASED"
            and
            not is_current_released_edit
        ):

            flash(
                (
                    "Historical released recipe cannot be edited. "
                    "Open the current production version."
                ),
                "error"
            )

            return redirect(
                f"/recipe-editor/{value['recipe_id']}"
            )

        active_operation_lock = _active_recipe_operation_lock(value["recipe_id"])
        if active_operation_lock:
            flash(
                "Recipe edit is blocked because "
                + _format_lock_owner(active_operation_lock)
                + " is still running. Wait until it reaches 100% success/failure.",
                "warning"
            )
            return redirect(f"/recipe-editor/{value['recipe_id']}")

        edit_lock_result = _acquire_recipe_edit_lock(value["recipe_id"])
        if not edit_lock_result.get("acquired"):
            active_lock = edit_lock_result.get("active_lock")
            flash(
                "Recipe is currently being edited by "
                + _format_lock_owner(active_lock)
                + ". Please wait until that user saves/closes or the edit lock expires.",
                "warning"
            )
            return redirect(f"/recipe-editor/{value['recipe_id']}")

        edit_lock_id = (edit_lock_result.get("lock") or {}).get("id")

        if request.method == "POST":

            try:

                new_value = float(
                    request.form[
                        "parameter_value"
                    ]
                )

            except Exception:

                flash(
                    "Enter a valid numeric parameter value.",
                    "error"
                )

                RecipeResourceLockManager.release_lock(
                    edit_lock_id,
                    reason="PARAMETER_EDIT_VALIDATION_FAILED"
                )

                return redirect(
                    f"/recipe-editor/edit/{value_id}"
                )

            if (
                value.get(
                    "min_value"
                )
                is not None
                and
                new_value < value["min_value"]
            ):

                flash(
                    (
                        "Parameter value is below minimum limit "
                        f"({value['min_value']})."
                    ),
                    "error"
                )

                RecipeResourceLockManager.release_lock(
                    edit_lock_id,
                    reason="PARAMETER_EDIT_VALIDATION_FAILED"
                )

                return redirect(
                    f"/recipe-editor/edit/{value_id}"
                )

            if (
                value.get(
                    "max_value"
                )
                is not None
                and
                new_value > value["max_value"]
            ):

                flash(
                    (
                        "Parameter value is above maximum limit "
                        f"({value['max_value']})."
                    ),
                    "error"
                )

                RecipeResourceLockManager.release_lock(
                    edit_lock_id,
                    reason="PARAMETER_EDIT_VALIDATION_FAILED"
                )

                return redirect(
                    f"/recipe-editor/edit/{value_id}"
                )

            change_reason = (
                request.form.get(
                    "change_reason"
                )
                or
                "Recipe Parameter Update"
            ).strip()

            if not change_reason:

                change_reason = (
                    "Recipe Parameter Update"
                )

            change_source = "CURRENT_RELEASED_EDIT"

            if not is_current_released_edit:

                change_source = "DRAFT_RECIPE_EDIT"

            result = RecipeParameterValueManager.update_recipe_value(

                value_id=value_id,

                new_value=new_value,

                changed_by=session.get(
                    "username"
                ),

                change_reason=change_reason,

                user_role=session.get(
                    "role",
                    "EDITOR"
                ),

                change_source=change_source,

                client_ip=request.remote_addr,

                workstation_name=request.headers.get(
                    "X-Forwarded-Host",
                    request.host
                )

            )

            if result.get(
                "success"
            ) and result.get(
                "changed"
            ):

                flash(
                    (
                        "Parameter updated and audited: "
                        f"{result.get('old_value')} -> "
                        f"{result.get('new_value')}"
                    ),
                    "success"
                )

            elif result.get(
                "success"
            ):

                flash(
                    result.get(
                        "message",
                        "No parameter change detected."
                    ),
                    "info"
                )

            else:

                flash(
                    result.get(
                        "message",
                        "Parameter update failed."
                    ),
                    "error"
                )

            RecipeResourceLockManager.release_lock(
                edit_lock_id,
                reason="PARAMETER_EDIT_COMPLETED"
            )

            return redirect(
                f"/recipe-editor/{value['recipe_id']}"
            )

        return render_template(

            "recipes/edit_value.html",

            value=value,

            recipe=recipe,

            is_current_released_edit=is_current_released_edit,

            edit_lock_id=edit_lock_id

        )


    @app.route(
        "/recipe-editor/edit/<int:value_id>/cancel",
        methods=["POST"]
    )
    def cancel_recipe_value_edit(value_id):
        """Explicitly release the current user's edit lock and return to editor."""
        if not session.get("username"):
            return redirect("/")

        value = RecipeParameterValueManager.get_recipe_value_by_id(value_id)
        if not value:
            flash("Recipe parameter value not found.", "error")
            return redirect("/recipes")

        RecipeResourceLockManager.release_current_user_resource(
            resource_type="RECIPE_EDIT",
            resource_id=value["recipe_id"],
            username=session.get("username"),
            session_id=session.get("session_id"),
            reason="PARAMETER_EDIT_CANCELLED_BY_USER"
        )

        flash("Recipe edit lock released.", "info")
        return redirect(f"/recipe-editor/{value['recipe_id']}")

    @app.route(
        "/recipe-editor/edit/<int:value_id>/release-lock",
        methods=["POST"]
    )
    def release_recipe_value_edit_lock(value_id):
        """AJAX/beacon release for edit-page close/back navigation."""
        if not session.get("username"):
            return jsonify({"ok": False, "message": "Login required."}), 401

        value = RecipeParameterValueManager.get_recipe_value_by_id(value_id)
        if not value:
            return jsonify({"ok": False, "message": "Parameter not found."}), 404

        released = RecipeResourceLockManager.release_current_user_resource(
            resource_type="RECIPE_EDIT",
            resource_id=value["recipe_id"],
            username=session.get("username"),
            session_id=session.get("session_id"),
            reason="PARAMETER_EDIT_PAGE_CLOSED"
        )

        return jsonify({"ok": True, "released": int(released or 0)})

    @app.route(
        "/recipe-editor/history/<int:value_id>"
    )
    def recipe_value_history(

        value_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        value = (
            RecipeParameterValueManager
            .get_recipe_value_by_id(
                value_id
            )
        )

        history = (
            RecipeParameterAuditManager
            .get_parameter_history(
                value_id
            )
        )

        for row in history:

            row["changed_at_ist"] = (
                utc_to_ist(
                    row["changed_at"]
                )
            )

        return render_template(

            "recipes/value_history.html",

            value=value,

            history=history

        )

    @app.route(
        "/recipe-editor/versions/<int:recipe_id>"
    )
    def recipe_editor_versions(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        if not role_can(
            session.get(
                "role"
            ),
            "recipe_edit"
        ):

            return _deny(
                "Your role cannot create recipe versions.",
                f"/recipe-editor/{recipe_id}"
            )

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        versions = (
            RecipeVersionManager
            .get_recipe_record_versions(
                recipe_id
            )
        )
        
        for row in versions:

            row["created_at_ist"] = (
                utc_to_ist(
                    row["created_at"]
                )
            )

            row["updated_at_ist"] = (
                utc_to_ist(
                    row["updated_at"]
                )
            )

        return render_template(

            "recipes/versions.html",

            recipe=recipe,

            versions=versions

        )

    @app.route(
        "/recipe-editor/create-version/<int:recipe_id>",
        methods=["GET", "POST"]
    )
    def recipe_editor_create_version(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        if not role_can(
            session.get(
                "role"
            ),
            "recipe_download"
        ):

            return _deny(
                "Your role cannot access PLC buffer operations.",
                f"/recipe-editor/{recipe_id}"
            )

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if (
            recipe
            and
            recipe["status"] == "RELEASED"
        ):

            flash(
                (
                    "Released recipes do not use snapshots. "
                    "Edit the current production version directly with audit."
                ),
                "error"
            )

            return redirect(
                f"/recipe-editor/{recipe_id}"
            )

        if request.method == "POST":

            RecipeVersionManager.create_version(

                recipe_id=recipe_id,

                version_comment=request.form[
                    "version_comment"
                ],

                created_by=session.get(
                    "username"
                )

            )

            return redirect(
                f"/recipe-editor/versions/{recipe_id}"
            )

        return render_template(

            "recipes/create_version.html",

            recipe=recipe

        )

    @app.route(
        "/recipe-editor/production-revision/<int:recipe_id>",
        methods=["POST"]
    )
    def recipe_editor_production_revision(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        if not role_can(
            session.get(
                "role"
            ),
            "recipe_edit"
        ):

            return _deny(
                "Your role cannot create production revisions.",
                f"/recipe-editor/{recipe_id}"
            )

        remarks = (
            request.form.get(
                "remarks"
            )
            or
            "Production fast edit"
        ).strip()

        success, message, new_recipe_id = (
            RecipeVersionManager
            .create_production_revision(

                recipe_id=recipe_id,

                version_comment=remarks,

                created_by=session.get(
                    "username"
                ),

                user_role=session.get(
                    "role",
                    "PRODUCTION"
                )

            )
        )

        if success:

            flash(
                message,
                "success"
            )

        else:

            flash(
                message,
                "error"
            )

        if new_recipe_id:

            return redirect(
                f"/recipe-editor/{new_recipe_id}"
            )

        return redirect(
            f"/recipe-editor/{recipe_id}"
        )

    @app.route(
        "/recipe-editor/release-production-revision/<int:recipe_id>",
        methods=["POST"]
    )
    def recipe_editor_release_production_revision(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        if not role_can(
            session.get(
                "role"
            ),
            "recipe_approve"
        ):

            return _deny(
                "Only Technology or Admin can release production revisions.",
                f"/recipe-editor/{recipe_id}"
            )

        remarks = (
            request.form.get(
                "remarks"
            )
            or
            ""
        ).strip()

        success, message = (
            RecipeVersionManager
            .release_production_revision(

                recipe_id=recipe_id,

                released_by=session.get(
                    "username"
                ),

                remarks=remarks,

                user_role=session.get(
                    "role",
                    "PRODUCTION"
                )

            )
        )

        if success:

            flash(
                message,
                "success"
            )

        else:

            flash(
                message,
                "error"
            )

        return redirect(
            f"/recipe-editor/{recipe_id}"
        )

    @app.route(
        "/recipe-editor/restore-version/<int:version_id>"
    )
    def recipe_editor_restore_version(

        version_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        if not role_can(
            session.get(
                "role"
            ),
            "recipe_edit"
        ):

            return _deny(
                "Your role cannot restore recipe versions.",
                request.referrer
                or
                "/dashboard"
            )

        version = (
            RecipeVersionManager
            .get_version_by_id(
                version_id
            )
        )

        if not version:

            flash(
                "Recipe version not found",
                "error"
            )

            return redirect(
                request.referrer
                or
                "/"
            )

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                version["recipe_id"]
            )
        )

        if (
            recipe
            and
            recipe["status"] == "RELEASED"
        ):

            flash(
                (
                    "Released recipe restore is blocked. "
                    "Edit the current production version directly with audit."
                ),
                "error"
            )

            return redirect(
                f"/recipe-editor/versions/{version['recipe_id']}"
            )

        RecipeVersionManager.restore_version(

            recipe_version_id=version_id,

            restored_by=session.get(
                "username"
            )

        )

        return redirect(
            request.referrer
            or "/dashboard"
        )
        
    @app.route(
        "/recipe-editor/status/<int:recipe_id>/<status>",
        methods=["GET", "POST"]
    )
    def recipe_status_change(

        recipe_id,

        status

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        valid_status = [

            "DRAFT",

            "REVIEW",

            "APPROVED"

        ]

        if status not in valid_status:

            return redirect("/")

        if (
            status == "REVIEW"
            and
            not role_can(
                session.get(
                    "role"
                ),
                "recipe_submit_review"
            )
        ):

            return _deny(
                "Your role cannot submit recipes for review.",
                f"/recipe-editor/{recipe_id}"
            )

        if (
            status in [
                "APPROVED",
                "DRAFT"
            ]
            and
            not role_can(
                session.get(
                    "role"
                ),
                "recipe_approve"
            )
        ):

            return _deny(
                "Only Technology or Admin can approve or reject recipes.",
                f"/recipe-editor/{recipe_id}"
            )

        remarks = (
            request.form.get("remarks")
            or
            request.args.get("remarks")
            or
            ""
        ).strip()

        if status == "REVIEW":

            success, message = (
                RecipeApprovalManager
                .submit_for_review(

                    recipe_id=recipe_id,

                    username=session["username"],

                    remarks=remarks

                )
            )

        elif status == "APPROVED":

            success, message = (
                RecipeApprovalManager
                .approve_recipe(

                    recipe_id=recipe_id,

                    username=session["username"],

                    remarks=remarks

                )
            )

        elif status == "DRAFT":

            if not remarks:

                flash(
                    "Rejection remarks required",
                    "error"
                )

                return redirect(
                    f"/recipe-editor/{recipe_id}"
                )

            success, message = (
                RecipeApprovalManager
                .reject_recipe(

                    recipe_id=recipe_id,

                    username=session["username"],

                    remarks=remarks

                )
            )

        else:

            success = False

            message = (
                "Direct release is blocked. "
                "Approve recipe to auto release."
            )

        if success:

            flash(
                message,
                "success"
            )

        else:

            flash(
                message,
                "error"
            )

        return redirect(
            f"/recipe-editor/{recipe_id}"
        )
        
    @app.route(
        "/recipe-editor/status-history/<int:recipe_id>"
    )
    def recipe_status_history(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        history = (
            RecipeStatusHistoryManager
            .get_history(
                recipe_id
            )
        )

        for row in history:

            row["changed_at_ist"] = (
                utc_to_ist(
                    row["changed_at"]
                )
            )

        return render_template(

            "recipes/status_history.html",

            history=history

        )

    @app.route(
        "/recipe-editor/download-preparation/<int:recipe_id>",
        methods=["GET", "POST"]
    )
    def recipe_download_preparation(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        if not role_can(
            session.get(
                "role"
            ),
            "recipe_download"
        ):

            flash(
                "Your role can view recipe values but cannot access PLC buffer operations.",
                "warning"
            )

            return redirect(
                f"/recipe-editor/{recipe_id}"
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

            return redirect("/")

        if (
            recipe.get(
                "version_usage_status"
            )
            ==
            "HISTORY_RELEASED"
            and
            recipe.get(
                "current_released_recipe_id"
            )
        ):

            flash(
                "Historical released recipe opened. "
                "Buffer operations moved to current production version.",
                "error"
            )

            return redirect(
                "/recipe-editor/download-preparation/"
                f"{recipe['current_released_recipe_id']}"
            )

        active_operation_lock = _active_recipe_operation_lock(recipe_id)
        if active_operation_lock:
            flash(
                "PLC buffer page is locked by "
                + _format_lock_owner(active_operation_lock)
                + ". Wait until operation reaches 100% success/failure.",
                "warning"
            )
            return redirect("/recipes")

        download_eligibility = (
            RecipeDownloadEligibilityManager
            .check_eligibility(
                recipe_id
            )
        )

        available_plcs = (
            PLCDownloadPreparationManager
            .get_available_plcs(
                recipe_id
            )
        )

        selected_plc_id = (
            request.form.get(
                "plc_id"
            )
            or
            request.args.get(
                "plc_id"
            )
            or
            ""
        )

        if (
            not selected_plc_id
            and
            available_plcs
        ):

            selected_plc_id = str(
                available_plcs[0]["id"]
            )

        operation_result = None

        if request.method == "POST":

            if not selected_plc_id:

                flash(
                    "Select PLC for recipe buffer operation",
                    "error"
                )

            else:

                try:

                    selected_plc_id_int = int(
                        selected_plc_id
                    )

                except Exception:

                    selected_plc_id_int = 0

                action = request.form.get(
                    "action",
                    ""
                ) or request.form.get(
                    "selected_action",
                    ""
                )

                if not role_can(
                    session.get(
                        "role"
                    ),
                    _buffer_operation_capability(
                        action
                    )
                ):

                    flash(
                        "Your role cannot run this PLC buffer operation.",
                        "error"
                    )

                    return redirect(
                        f"/recipe-editor/download-preparation/{recipe_id}"
                    )

                operation_result = (
                    PLCBufferOperationManager
                    .run_operation(

                        recipe_id=recipe_id,

                        plc_id=selected_plc_id_int,

                        operation=action,

                        username=session.get(
                            "username"
                        ),

                        user_role=session.get(
                            "role",
                            "PRODUCTION"
                        )

                    )
                )

        operation_context = (
            PLCBufferOperationManager
            .get_operation_context(

                recipe_id=recipe_id,

                plc_id=selected_plc_id

            )
        )

        recent_operations = (
            PLCOperationJobManager
            .get_recent_for_recipe(

                recipe_id=recipe_id,

                limit=8

            )
        )

        return render_template(

            "recipes/download_preparation.html",

            recipe=recipe,

            download_eligibility=download_eligibility,

            available_plcs=available_plcs,

            selected_plc_id=str(
                selected_plc_id
            ),

            operation_context=operation_context,

            operation_result=operation_result,

            recent_operations=recent_operations,

            can_edit_recipe=role_can(
                session.get(
                    "role"
                ),
                "recipe_edit"
            ),

            can_download_recipe=role_can(
                session.get(
                    "role"
                ),
                "recipe_download"
            )

        )

    @app.route(
        "/recipe-editor/download-preparation/<int:recipe_id>/start",
        methods=["POST"]
    )
    def recipe_download_preparation_start(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return jsonify({
                "success": False,
                "message": "Login required."
            }), 401

        if not role_can(
            session.get(
                "role"
            ),
            "recipe_download"
        ):

            return jsonify({
                "success": False,
                "message": "Your role cannot access PLC buffer operations."
            }), 403

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            return jsonify({
                "success": False,
                "message": "Recipe not found."
            }), 404

        if (
            recipe.get(
                "version_usage_status"
            )
            ==
            "HISTORY_RELEASED"
        ):

            return jsonify({
                "success": False,
                "message": (
                    "Historical released recipe opened. "
                    "Open the current production version."
                ),
                "current_recipe_id": recipe.get(
                    "current_released_recipe_id"
                )
            }), 409

        action = (
            request.form.get(
                "action",
                ""
            )
            or
            request.form.get(
                "selected_action",
                ""
            )
        )

        if action not in PLCBufferOperationManager.OPERATIONS:

            return jsonify({
                "success": False,
                "message": "Unknown PLC buffer operation."
            }), 400

        if not role_can(
            session.get(
                "role"
            ),
            _buffer_operation_capability(
                action
            )
        ):

            return jsonify({
                "success": False,
                "message": "Your role cannot run this PLC buffer operation."
            }), 403

        selected_plc_id = (
            request.form.get(
                "plc_id"
            )
            or
            ""
        )

        try:

            selected_plc_id_int = int(
                selected_plc_id
            )

        except Exception:

            selected_plc_id_int = 0

        if not selected_plc_id_int:

            return jsonify({
                "success": False,
                "message": "Select PLC for recipe buffer operation."
            }), 400

        recipe_lock = _active_recipe_operation_lock(recipe_id)
        if recipe_lock:
            return jsonify({
                "success": False,
                "message": "Recipe is already locked by " + _format_lock_owner(recipe_lock) + ". Wait until operation reaches 100% success/failure.",
                "active_lock_id": recipe_lock.get("id")
            }), 409

        plc_lock = _active_plc_operation_lock(selected_plc_id_int)
        if plc_lock:
            return jsonify({
                "success": False,
                "message": "PLC is already locked by " + _format_lock_owner(plc_lock) + ". Wait until operation reaches 100% success/failure.",
                "active_lock_id": plc_lock.get("id")
            }), 409

        username = session.get(
            "username"
        )

        user_role = session.get(
            "role",
            "PRODUCTION"
        )

        active_job = (
            PLCOperationJobManager
            .get_active_for_plc(
                selected_plc_id_int
            )
        )

        if active_job:

            return jsonify({
                "success": False,
                "message": (
                    "Another PLC buffer operation is already running for this PLC. "
                    "Wait until it reaches 100% success or failure before starting a new command."
                ),
                "active_job_id": active_job.get(
                    "id"
                ),
                "active_operation": active_job.get(
                    "title"
                ),
                "active_started_by": active_job.get(
                    "started_by"
                ),
                "active_status_url": (
                    "/recipe-editor/download-preparation/job/"
                    + str(
                        active_job.get(
                            "id"
                        )
                    )
                )
            }), 409

        ctx = _lock_context()
        recipe_operation_lock = RecipeResourceLockManager.acquire_lock(
            resource_type="RECIPE_OPERATION",
            resource_id=recipe_id,
            operation_type=action,
            username=username,
            user_role=user_role,
            session_id=ctx["session_id"],
            workstation_name=ctx["workstation_name"],
            client_ip=ctx["client_ip"],
            user_agent=ctx["user_agent"],
            ttl_minutes=180,
            notes="PLC buffer operation recipe lock"
        )
        if not recipe_operation_lock.get("acquired"):
            active_lock = recipe_operation_lock.get("active_lock")
            return jsonify({
                "success": False,
                "message": "Recipe is already locked by " + _format_lock_owner(active_lock) + ".",
                "active_lock_id": active_lock.get("id") if active_lock else None
            }), 409

        plc_operation_lock = RecipeResourceLockManager.acquire_lock(
            resource_type="PLC_OPERATION",
            resource_id=selected_plc_id_int,
            operation_type=action,
            username=username,
            user_role=user_role,
            session_id=ctx["session_id"],
            workstation_name=ctx["workstation_name"],
            client_ip=ctx["client_ip"],
            user_agent=ctx["user_agent"],
            ttl_minutes=180,
            notes="PLC buffer operation PLC lock"
        )
        if not plc_operation_lock.get("acquired"):
            RecipeResourceLockManager.release_lock(
                (recipe_operation_lock.get("lock") or {}).get("id"),
                reason="PLC_OPERATION_LOCK_FAILED"
            )
            active_lock = plc_operation_lock.get("active_lock")
            return jsonify({
                "success": False,
                "message": "PLC is already locked by " + _format_lock_owner(active_lock) + ".",
                "active_lock_id": active_lock.get("id") if active_lock else None
            }), 409

        recipe_operation_lock_id = (recipe_operation_lock.get("lock") or {}).get("id")
        plc_operation_lock_id = (plc_operation_lock.get("lock") or {}).get("id")

        operation_title = (
            PLCBufferOperationManager
            .OPERATIONS[
                action
            ][
                "title"
            ]
        )

        job_id = (
            PLCOperationJobManager
            .create_job(

                recipe_id=recipe_id,

                plc_id=selected_plc_id_int,

                operation=action,

                title=operation_title,

                username=username,

                user_role=user_role

            )
        )

        def run_job():

            try:

                PLCBufferOperationManager.run_operation(

                    recipe_id=recipe_id,

                    plc_id=selected_plc_id_int,

                    operation=action,

                    username=username,

                    user_role=user_role,

                    status_job_id=job_id

                )

            except Exception as exc:

                PLCOperationJobManager.fail_job(
                    job_id=job_id,
                    message=str(
                        exc
                    )
                )

            finally:

                RecipeResourceLockManager.release_lock(
                    recipe_operation_lock_id,
                    reason="PLC_OPERATION_COMPLETED"
                )
                RecipeResourceLockManager.release_lock(
                    plc_operation_lock_id,
                    reason="PLC_OPERATION_COMPLETED"
                )

        thread = threading.Thread(
            target=run_job,
            daemon=True
        )

        thread.start()

        return jsonify({
            "success": True,
            "job_id": job_id,
            "status_url": (
                "/recipe-editor/download-preparation/job/"
                f"{job_id}"
            )
        })

    @app.route(
        "/recipe-editor/download-preparation/job/<job_id>"
    )
    def recipe_download_preparation_job_status(

        job_id

    ):

        if not session.get(
            "username"
        ):

            return jsonify({
                "success": False,
                "message": "Login required."
            }), 401

        job = (
            PLCOperationJobManager
            .get_job(
                job_id
            )
        )

        if not job:

            return jsonify({
                "success": False,
                "message": "Operation job not found."
            }), 404

        return jsonify({
            "success": True,
            "job": job,
            "done": job.get(
                "status"
            )
            in [
                "SUCCESS",
                "BLOCKED",
                "ERROR"
            ]
        })
