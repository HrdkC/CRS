from flask import (
    render_template,
    request,
    redirect,
    session,
    flash,
    jsonify,
    current_app
)


from datetime import datetime, timezone

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

from database.recipe_bulk_change_service import (
    RecipeBulkChangeService
)

from utils.plc_worker_runtime_status import (
    PLCWorkerRuntimeStatus
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


def _job_timestamp_age_seconds(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            now = datetime.now(timezone.utc)
            return max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return max(0.0, (now - parsed).total_seconds())
    except (TypeError, ValueError):
        return None


def _no_store_json(payload, status=200):
    response = jsonify(payload)
    response.status_code = int(status)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _live_status_json_payload(live_status):
    """Return a stable, JSON-safe view of read-only PLC live status."""

    def scalar(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    groups = []
    for group in (live_status or {}).get("groups", []):
        items = []
        for item in group.get("items", []):
            tag = item.get("tag") or {}
            try:
                tag_name = tag.get("tag_name")
            except AttributeError:
                try:
                    tag_name = tag["tag_name"]
                except Exception:
                    tag_name = None

            items.append({
                "purpose": item.get("purpose"),
                "label": item.get("label"),
                "tag_name": tag_name or "Not mapped",
                "value": scalar(item.get("value")),
                "expected_text": item.get("expected_text") or "Readable",
                "status": item.get("status") or "missing",
                "status_text": item.get("status_text") or "Not Checked",
                "message": item.get("message") or "",
            })

        groups.append({
            "title": group.get("title") or "PLC Status",
            "items": items,
        })

    return {
        "connected": bool((live_status or {}).get("connected")),
        "status": (live_status or {}).get("status") or "NOT_CHECKED",
        "summary": (live_status or {}).get("summary") or "Live PLC status was not checked.",
        "groups": groups,
        "issues": [str(issue) for issue in (live_status or {}).get("issues", [])],
    }


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

        if not recipe:
            flash(
                "Recipe is archived or no longer available in the active list.",
                "warning"
            )
            return redirect("/recipes")

        search_text = request.args.get(
            "search",
            ""
        )

        modified_only = request.args.get(
            "modified_only",
            "0"
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

        all_template_values = (
            RecipeParameterValueManager
            .get_recipe_values(
                recipe_id,
                include_inactive=True
            )
        )

        active_values = [
            row
            for row in all_template_values
            if int(row.get("used", 1) or 0) == 1
        ]

        inactive_count = (
            len(all_template_values)
            -
            len(active_values)
        )

        editor_metrics = _build_recipe_editor_metrics(
            active_values
        )

        if parameter_scope == "all":

            values = list(all_template_values)

        elif parameter_scope == "inactive":

            values = [
                row
                for row in all_template_values
                if int(row.get("used", 1) or 0) == 0
            ]

        else:

            values = list(active_values)

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

            "parameter_scope": parameter_scope,

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

        can_role_download_recipe = role_can(
            user_role,
            "recipe_download"
        )
        can_download_recipe = can_role_download_recipe

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
            can_role_download_recipe=can_role_download_recipe,

            can_copy_recipe=can_copy_recipe,

            edit_lock_reason=edit_lock_reason,

            search_text=search_text,

            modified_only=modified_only,

            parameter_scope=parameter_scope,

            active_parameter_count=len(active_values),

            inactive_parameter_count=inactive_count,

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
        "/recipe-editor/<int:recipe_id>/plc-buffer-access-status",
        methods=["GET"]
    )
    def recipe_editor_plc_buffer_access_status(recipe_id):
        """Report shared PLC-buffer availability without touching the PLC."""

        if not session.get("username"):
            return jsonify({
                "success": False,
                "message": "Login required."
            }), 401

        if not role_can(session.get("role"), "recipe_download"):
            return jsonify({
                "success": False,
                "message": "Your role cannot access PLC buffer operations."
            }), 403

        recipe = RecipeManager.get_recipe_by_id(recipe_id)
        if not recipe:
            return jsonify({
                "success": False,
                "message": "Recipe not found."
            }), 404

        active_operation_lock = _active_recipe_operation_lock(recipe_id)
        available = active_operation_lock is None
        response = jsonify({
            "success": True,
            "recipe_id": recipe_id,
            "plc_buffer_available": available,
            "operation_active": not available,
            "message": (
                "PLC Buffer is available."
                if available
                else "PLC buffer operation is in progress in another login."
            ),
            "href": f"/recipe-editor/download-preparation/{recipe_id}",
        })
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

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

        search_text = (
            request.args.get(
                "search",
                ""
            )
            or
            ""
        ).strip()

        def _filter_bulk_rows(source_rows):

            if not search_text:

                return list(source_rows)

            search_upper = search_text.upper()

            return [
                row
                for row in source_rows
                if (
                    search_upper
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

        def _clone_row(row):

            if hasattr(row, "copy"):

                return row.copy()

            return dict(row)

        def _posted_or_existing(form, field_name, existing_value):

            if field_name in form:

                return form.get(field_name)

            if existing_value is None:

                return ""

            return str(existing_value)

        def _rows_with_posted_values(display_rows, form):

            hydrated_rows = []

            for row in display_rows:

                row_copy = _clone_row(row)

                row_id = str(row_copy["id"])

                row_copy["form_parameter_value"] = _posted_or_existing(
                    form,
                    f"parameter_value_{row_id}",
                    row_copy.get("parameter_value")
                )

                row_copy["form_parameter_name"] = _posted_or_existing(
                    form,
                    f"parameter_name_{row_id}",
                    row_copy.get("parameter_name")
                )

                row_copy["form_unit"] = _posted_or_existing(
                    form,
                    f"unit_{row_id}",
                    row_copy.get("unit")
                )

                row_copy["form_min_value"] = _posted_or_existing(
                    form,
                    f"min_value_{row_id}",
                    row_copy.get("min_value")
                )

                row_copy["form_max_value"] = _posted_or_existing(
                    form,
                    f"max_value_{row_id}",
                    row_copy.get("max_value")
                )

                row_copy["form_default_value"] = _posted_or_existing(
                    form,
                    f"default_value_{row_id}",
                    row_copy.get("default_value")
                )

                row_copy["form_used"] = (
                    1
                    if form.get(f"used_{row_id}") == "1"
                    else
                    0
                    if f"used_present_{row_id}" in form
                    else
                    int(row_copy.get("used", 1) or 0)
                )

                hydrated_rows.append(row_copy)

            return hydrated_rows

        def _norm(value):

            if value is None:

                return ""

            return str(value).strip()

        def _row_has_posted_change(row, form):

            row_id = str(row["id"])

            compare_fields = [
                (
                    f"parameter_value_{row_id}",
                    row.get("parameter_value")
                )
            ]

            if can_edit_details:

                compare_fields.extend([
                    (
                        f"parameter_name_{row_id}",
                        row.get("parameter_name")
                    ),
                    (
                        f"unit_{row_id}",
                        row.get("unit")
                    ),
                    (
                        f"min_value_{row_id}",
                        row.get("min_value")
                    ),
                    (
                        f"max_value_{row_id}",
                        row.get("max_value")
                    ),
                    (
                        f"default_value_{row_id}",
                        row.get("default_value")
                    )
                ])

                if f"used_present_{row_id}" in form:

                    posted_used = 1 if form.get(f"used_{row_id}") == "1" else 0

                    if posted_used != int(row.get("used", 1) or 0):

                        return True

            for field_name, old_value in compare_fields:

                if field_name not in form:

                    continue

                if _norm(form.get(field_name)) != _norm(old_value):

                    return True

            return False

        def _render_bulk_edit(
            display_rows,
            selected_ids=None,
            validation_errors=None,
            change_reason=""
        ):

            return render_template(
                "recipes/bulk_edit_parameters.html",
                recipe=recipe,
                rows=display_rows,
                selected_ids=set(str(value_id) for value_id in (selected_ids or [])),
                validation_errors=validation_errors or [],
                search_text=search_text,
                can_edit_details=can_edit_details,
                change_reason=change_reason or ""
            )

        all_rows = (
            RecipeParameterValueManager
            .get_recipe_values(
                recipe_id,
                include_inactive=True
            )
        )

        rows = _filter_bulk_rows(all_rows)

        if request.method == "POST":

            row_by_value_id = {
                str(row["id"]): row
                for row in all_rows
            }

            posted_rows = _rows_with_posted_values(
                rows,
                request.form
            )

            selected_ids = set(
                request.form.getlist(
                    "selected_value_id"
                )
            )

            changed_ids = {
                str(row["id"])
                for row in all_rows
                if _row_has_posted_change(
                    row,
                    request.form
                )
            }

            # Browser-side JavaScript also auto-selects changed rows, but this
            # backend rule is the safety net. If the user forgets to tick a row,
            # changed rows are still saved and typed values are not lost.
            selected_ids.update(
                changed_ids
            )

            selected_ids = {
                value_id
                for value_id in selected_ids
                if value_id in row_by_value_id
            }

            change_reason = (
                request.form.get(
                    "change_reason"
                )
                or
                ""
            ).strip()

            if not selected_ids:

                validation_errors = [
                    (
                        "No changed or selected parameter row was found. "
                        "Edit a row or tick one row before saving. Typed values have been kept on this page."
                    )
                ]

                flash(
                    "Select or edit at least one parameter row to save. Typed values were kept.",
                    "error"
                )

                return _render_bulk_edit(
                    posted_rows,
                    selected_ids=selected_ids,
                    validation_errors=validation_errors,
                    change_reason=change_reason
                )

            if not change_reason:

                validation_errors = [
                    "Enter a change reason before saving selected parameters. Typed values have been kept on this page."
                ]

                flash(
                    "Enter a change reason before saving selected parameters. Typed values were kept.",
                    "error"
                )

                return _render_bulk_edit(
                    posted_rows,
                    selected_ids=selected_ids,
                    validation_errors=validation_errors,
                    change_reason=change_reason
                )

            validation_errors = []

            parsed_changes = {}

            final_names = {}

            for row in all_rows:

                row_id = str(row["id"])

                selected = row_id in selected_ids

                try:

                    value = (
                        float(
                            request.form.get(
                                f"parameter_value_{row_id}",
                                row["parameter_value"]
                            )
                        )
                        if selected
                        else
                        row["parameter_value"]
                    )

                    if selected and can_edit_details:

                        parameter_name = (
                            request.form.get(
                                f"parameter_name_{row_id}",
                                row.get("parameter_name") or ""
                            )
                            or
                            ""
                        ).strip()

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

                        used = (
                            1
                            if request.form.get(f"used_{row_id}") == "1"
                            else
                            0
                        )

                    else:

                        parameter_name = row.get("parameter_name") or ""
                        unit = row.get("unit") or ""
                        min_value = row.get("min_value")
                        max_value = row.get("max_value")
                        default_value = row.get("default_value")
                        used = int(row.get("used", 1) or 0)

                    # PLC index is master mapping data. It is intentionally not
                    # editable from Bulk Edit and is never read from the form.
                    plc_array_index = row.get("plc_array_index")

                    if selected and can_edit_details and not parameter_name:

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
                        "default_value": default_value,
                        "used": used
                    }

                    if parameter_name:

                        final_name_key = parameter_name.upper()

                        if final_name_key in final_names:

                            validation_errors.append(
                                f"Duplicate parameter name: {parameter_name}."
                            )

                        final_names[final_name_key] = row["id"]

                except Exception as exc:

                    validation_errors.append(
                        f"Tag {row.get('tag_index')}: invalid input ({exc})."
                    )

            unknown_ids = [
                value_id
                for value_id in request.form.getlist(
                    "selected_value_id"
                )
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

                return _render_bulk_edit(
                    posted_rows,
                    selected_ids=selected_ids,
                    validation_errors=validation_errors[:20],
                    change_reason=change_reason
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

                return _render_bulk_edit(
                    posted_rows,
                    selected_ids=selected_ids,
                    validation_errors=[
                        "Recipe edit lock is active. Typed values have been kept on this page."
                    ],
                    change_reason=change_reason
                )

            edit_lock_id = (
                edit_lock_result.get("lock")
                or
                {}
            ).get("id")

            changes = []
            for value_id in selected_ids:
                parsed = parsed_changes[value_id]
                row = parsed["row"]
                changes.append({
                    "value_id": int(value_id),
                    "value": parsed["value"],
                    "parameter_name": parsed["parameter_name"],
                    "unit": parsed["unit"],
                    "min_value": parsed["min_value"],
                    "max_value": parsed["max_value"],
                    "default_value": parsed["default_value"],
                    "used": parsed["used"],
                    "parameter_definition_id": row["parameter_definition_id"],
                })

            try:
                bulk_result = RecipeBulkChangeService.apply(
                    recipe_id=recipe_id,
                    changes=changes,
                    changed_by=session.get("username"),
                    user_role=user_role,
                    change_reason=change_reason,
                    can_edit_details=can_edit_details,
                    client_ip=request.remote_addr,
                    workstation_name=request.headers.get(
                        "X-Forwarded-Host", request.host
                    ),
                )

                if not bulk_result.get("success"):
                    flash(
                        bulk_result.get(
                            "message",
                            "Bulk save failed and was rolled back."
                        ),
                        "error"
                    )
                    return _render_bulk_edit(
                        posted_rows,
                        selected_ids=selected_ids,
                        validation_errors=[
                            "No selected row was saved. Typed values have been kept."
                        ],
                        change_reason=change_reason
                    )

                flash(
                    (
                        "Bulk parameter save completed atomically: "
                        f"{bulk_result.get('changed_count', 0)} value change(s), "
                        f"{bulk_result.get('detail_changed_count', 0)} detail field change(s). "
                        "PLC index mapping was not changed."
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

        return _render_bulk_edit(
            rows,
            selected_ids=set(),
            validation_errors=[],
            change_reason=""
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

        if not recipe:
            flash(
                "Recipe is archived or no longer available for editing.",
                "warning"
            )
            return redirect("/recipes")

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

        if not recipe:

            flash(
                "Recipe not found.",
                "error"
            )

            return redirect(
                "/recipes"
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
                ),

                user_role=session.get(
                    "role",
                    "PRODUCTION"
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
        "/recipe-editor/restore-version/<int:version_id>",
        methods=["POST"]
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

        try:
            result = RecipeVersionManager.restore_version(

                recipe_version_id=version_id,

                restored_by=session.get(
                    "username"
                ),

                reason=(
                    request.form.get("reason")
                    or f"Restore snapshot {version_id}"
                ).strip(),

                user_role=session.get(
                    "role",
                    "PRODUCTION"
                ),

                client_ip=request.remote_addr,

                workstation_name=(
                    request.headers.get("X-Forwarded-Host")
                    or request.host
                )

            )
            flash(
                f"Recipe snapshot restored: {result['changed_count']} parameter change(s).",
                "success"
            )
        except (ValueError, RuntimeError) as exc:
            flash(str(exc), "error")

        return redirect(
            request.referrer
            or "/dashboard"
        )
        
    @app.route(
        "/recipe-editor/status/<int:recipe_id>/<status>",
        methods=["POST"]
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

        live_tag_status = (
            PLCBufferOperationManager
            .get_live_tag_status(

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

            live_tag_status=live_tag_status,

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
        "/recipe-editor/download-preparation/<int:recipe_id>/live-status",
        methods=["GET"]
    )
    def recipe_download_preparation_live_status(recipe_id):
        """Read current interlock/handshake values without changing PLC data."""

        if not session.get("username"):
            return jsonify({
                "success": False,
                "message": "Login required."
            }), 401

        if not role_can(session.get("role"), "recipe_download"):
            return jsonify({
                "success": False,
                "message": "Your role cannot access PLC buffer live status."
            }), 403

        recipe = RecipeManager.get_recipe_by_id(recipe_id)
        if not recipe:
            return jsonify({
                "success": False,
                "message": "Recipe not found."
            }), 404

        selected_plc_id = request.args.get("plc_id", "").strip()
        try:
            selected_plc_id = int(selected_plc_id) if selected_plc_id else None
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid PLC selection."
            }), 400

        live_status = PLCBufferOperationManager.get_live_tag_status(
            recipe_id=recipe_id,
            plc_id=selected_plc_id,
        )

        response = jsonify({
            "success": True,
            "live_status": _live_status_json_payload(live_status),
        })
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

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

        worker_status = PLCWorkerRuntimeStatus.get_status(max_age_seconds=5.0)
        if not worker_status.get("online"):
            return jsonify({
                "success": False,
                "worker_offline": True,
                "message": (
                    "The durable CRS PLC worker is offline. "
                    "Start CRS with Start_CRS_With_PLC_Worker.bat and retry. "
                    "No PLC job was queued and no resource lock was taken."
                ),
                "worker_status": {
                    "state": worker_status.get("state") or "OFFLINE",
                    "age_seconds": worker_status.get("age_seconds"),
                },
            }), 503

        edit_lock = RecipeResourceLockManager.get_active_lock(
            "RECIPE_EDIT", recipe_id
        )
        if edit_lock:
            return jsonify({
                "success": False,
                "message": (
                    "Recipe is currently being edited. Save or cancel the edit "
                    "before starting a PLC buffer operation."
                ),
                "active_lock_id": edit_lock.get("id")
            }), 409

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

        try:
            job_id = PLCOperationJobManager.create_job(
                recipe_id=recipe_id,
                plc_id=selected_plc_id_int,
                operation=action,
                title=operation_title,
                username=username,
                user_role=user_role,
                recipe_lock_id=recipe_operation_lock_id,
                plc_lock_id=plc_operation_lock_id,
            )
        except Exception:
            RecipeResourceLockManager.release_lock(
                recipe_operation_lock_id, reason="PLC_JOB_QUEUE_FAILED"
            )
            RecipeResourceLockManager.release_lock(
                plc_operation_lock_id, reason="PLC_JOB_QUEUE_FAILED"
            )
            return jsonify({
                "success": False,
                "message": "Unable to queue the PLC operation. No PLC work was started."
            }), 500

        return jsonify({
            "success": True,
            "job_id": job_id,
            "queued": True,
            "message": (
                "Operation queued for the durable CRS PLC worker. "
                "The web process will not execute PLC writes."
            ),
            "status_url": (
                "/recipe-editor/download-preparation/job/" + str(job_id)
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

        try:
            job = PLCOperationJobManager.get_job(job_id)
        except Exception as exc:
            if PLCOperationJobManager.is_retryable_database_error(exc):
                return _no_store_json({
                    "success": False,
                    "retryable": True,
                    "message": (
                        "The PLC job database is briefly busy. CRS will retry "
                        "without unlocking the operation."
                    ),
                }, status=503)
            current_app.logger.exception(
                "Unable to read PLC operation job %s", job_id
            )
            return _no_store_json({
                "success": False,
                "retryable": True,
                "message": "PLC operation status is temporarily unavailable.",
            }, status=503)

        if not job:
            return _no_store_json({
                "success": False,
                "message": "Operation job not found."
            }, status=404)

        is_owner = (job.get("started_by") or "").lower() == (
            session.get("username") or ""
        ).lower()
        can_supervise = role_can(session.get("role"), "audit_view")
        if not is_owner and not can_supervise:
            return _no_store_json({
                "success": False,
                "message": "You are not authorized to view this PLC operation."
            }, status=403)

        # Recover an old active row when the durable worker is demonstrably
        # online but idle and no longer owns this job.  This is a final safety
        # net for jobs created before terminal-status persistence was hardened.
        if job.get("status") in PLCOperationJobManager.ACTIVE_STATUSES:
            worker_status = PLCWorkerRuntimeStatus.get_status()
            heartbeat_age = _job_timestamp_age_seconds(
                job.get("heartbeat_at") or job.get("updated_at")
            )
            worker_owns_job = str(
                worker_status.get("current_job_id") or ""
            ) == str(job_id)
            worker_is_idle = (
                worker_status.get("online")
                and str(worker_status.get("state") or "").upper() == "IDLE"
                and not worker_owns_job
            )
            if worker_is_idle and heartbeat_age is not None and heartbeat_age >= 45:
                try:
                    PLCOperationJobManager.recover_orphaned_job(
                        job_id,
                        recovery_reason="STATUS_ENDPOINT_IDLE_WORKER_RECOVERY",
                    )
                    job = PLCOperationJobManager.get_job(job_id) or job
                except Exception:
                    current_app.logger.exception(
                        "Unable to recover orphaned PLC operation job %s", job_id
                    )

        return _no_store_json({
            "success": True,
            "job": job,
            "done": job.get("status") in PLCOperationJobManager.FINAL_STATUSES,
        })
