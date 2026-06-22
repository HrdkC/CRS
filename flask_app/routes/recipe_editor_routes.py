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

        edit_lock_reason = ""

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

            production_revision_source=production_revision_source,

            download_eligibility=download_eligibility,

            editor_metrics=editor_metrics,

            can_edit_values=can_edit_values,

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

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                value["recipe_id"]
            )
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

            RecipeParameterValueManager.update_recipe_value(

                value_id=value_id,

                new_value=new_value,

                changed_by=session.get(
                    "username"
                ),

                change_reason=change_reason,

                user_role=session.get(
                    "role",
                    "EDITOR"
                )

            )

            return redirect(
                f"/recipe-editor/{value['recipe_id']}"
            )

        return render_template(

            "recipes/edit_value.html",

            value=value

        )

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

            recent_operations=recent_operations

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

        username = session.get(
            "username"
        )

        user_role = session.get(
            "role",
            "PRODUCTION"
        )

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
