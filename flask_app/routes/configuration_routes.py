from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
)
import json
from urllib.parse import quote

from database.configuration_readiness_manager import (
    ConfigurationReadinessManager,
)
from database.stage_plc_tag_requirement_manager import (
    StagePLCTagRequirementManager,
)
from database.audit_manager import AuditManager
from database.plc_tag_manager import PLCTagManager
from database.plc_registry_manager import PLCRegistryManager
from flask_app.routes.phase_control_routes import (
    _initialize_standard_phase_master,
)
from flask_app.security.role_guard import role_can
from flask_app.stage_url_helper import (
    add_machine_stage_url_fields,
    get_machine_stage_context_by_code,
    machine_stage_url,
)


def _engineering_config_allowed():
    return (
        session.get("logged_in")
        and
        role_can(
            session.get("role"),
            "engineering_config",
        )
    )


def _decorate_report(report):
    context = report["context"]
    add_machine_stage_url_fields(context)

    report["setup_url"] = machine_stage_url(
        "/configuration",
        context=context,
    )
    report["recipes_url"] = machine_stage_url(
        "/recipes",
        context=context,
    )
    report["create_recipe_url"] = machine_stage_url(
        "/recipes/create",
        context=context,
    )
    report["parameters_url"] = machine_stage_url(
        "/parameters",
        context=context,
    )
    report["plc_tags_url"] = machine_stage_url(
        "/plc-tags",
        context=context,
    )
    report["phase_master_url"] = machine_stage_url(
        "/phase-controls",
        context=context,
    )
    report["phase_defaults_url"] = (
        machine_stage_url(
            "/configuration",
            context=context,
        )
        + "/phase-defaults"
    )
    report["plc_array_import_url"] = machine_stage_url(
        "/plc-array-import",
        context=context,
    )
    report["tag_setup_save_url"] = (
        machine_stage_url(
            "/configuration",
            context=context,
        )
        + "/tag-requirements"
    )
    report["tag_purpose_remap_url"] = (
        machine_stage_url(
            "/configuration",
            context=context,
        )
        + "/tag-purpose-remap"
    )
    report["plc_registry_save_url"] = (
        machine_stage_url(
            "/configuration",
            context=context,
        )
        + "/plc-registry"
    )
    report["plc_assignment_save_url"] = (
        machine_stage_url(
            "/configuration",
            context=context,
        )
        + "/plc-assignment"
    )
    report["plc_tag_seed_url"] = (
        machine_stage_url(
            "/configuration",
            context=context,
        )
        + "/seed-plc-tags"
    )
    report["plcs_url"] = "/plcs"
    report["plc_create_url"] = (
        "/plcs/create?machine_stage_id="
        + str(context["stage_id"])
        + "&return_to="
        + quote(report["setup_url"])
    )
    report["stage_plcs"] = PLCRegistryManager.get_plcs_for_stage(
        context["stage_id"],
        include_inactive=True,
    )
    report["active_stage_plcs"] = [
        plc
        for plc in report["stage_plcs"]
        if int(plc.get("active", 1) or 0) == 1
    ]
    report["assigned_plc"] = (
        report["active_stage_plcs"][0]
        if report["active_stage_plcs"]
        else (report["stage_plcs"][0] if report["stage_plcs"] else None)
    )
    report["all_plcs"] = PLCRegistryManager.get_all_plcs_with_machine_stage(
        include_inactive=True,
    )

    for plc in report["all_plcs"]:
        plc["is_current_stage"] = (
            int(plc.get("machine_stage_id") or 0)
            == int(context["stage_id"])
        )

    for section in report["sections"]:
        for item in section["items"]:
            purpose = item.get("action")
            if purpose:
                item["action_url"] = machine_stage_url(
                    "/plc-tags",
                    context=context,
                    query={
                        "purpose": purpose,
                        "online_search": 1,
                        "search": (
                            item.get("search_hint")
                            or item.get("default_tag_name")
                            or purpose.replace("_", " ").title()
                        ),
                    },
                )

    return report


def _summarize_tag_requirement(row):
    if not row:
        return {}
    keys = [
        "purpose",
        "label",
        "requirement_level",
        "expected_type",
        "array_required",
        "minimum_array_size",
        "array_start_index",
        "array_end_index",
        "default_tag_name",
        "search_hint",
        "active",
        "display_order",
    ]
    return {
        key: row.get(key)
        for key in keys
    }


def _audit_tag_requirement_changes(context, old_rows, new_rows, reason):
    old_by_purpose = {
        row.get("purpose"): _summarize_tag_requirement(row)
        for row in old_rows
    }
    new_by_purpose = {
        row.get("purpose"): _summarize_tag_requirement(row)
        for row in new_rows
    }
    purposes = sorted(set(old_by_purpose) | set(new_by_purpose))
    for purpose in purposes:
        old_value = old_by_purpose.get(purpose)
        new_value = new_by_purpose.get(purpose)
        if old_value == new_value:
            continue
        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PLC_TAG_REQUIREMENT_RULE_UPDATED",
            change_source="CONFIGURATION_CENTER",
            record_id=context["stage_id"],
            parameter_name=purpose,
            old_value=json.dumps(old_value, sort_keys=True),
            new_value=json.dumps(new_value, sort_keys=True),
            reason=reason,
            user_agent=request.headers.get("User-Agent", ""),
            forwarded_for=request.headers.get("X-Forwarded-For"),
            request_host=request.host,
        )



def _audit_plc_tag_bulk_changes(changes, reason):
    for item in changes or []:
        tag_id = item.get("id")
        tag_name = item.get("tag_name")
        for change in item.get("changes", []):
            try:
                AuditManager.log_event(
                    username=session.get("username"),
                    role=session.get("role"),
                    action="PLC_TAG_CONFIGURATION_UPDATED",
                    change_source="CONFIGURATION_CENTER",
                    record_id=tag_id,
                    parameter_name=f"{tag_name}.{change.get('field')}",
                    old_value=str(change.get("old") if change.get("old") is not None else ""),
                    new_value=str(change.get("new") if change.get("new") is not None else ""),
                    reason=reason,
                    user_agent=request.headers.get("User-Agent", ""),
                    forwarded_for=request.headers.get("X-Forwarded-For"),
                    request_host=request.host,
                )
            except Exception:
                pass


def register_configuration_routes(app):

    @app.route("/configuration")
    def configuration_center():
        if not _engineering_config_allowed():
            return redirect("/")

        reports = [
            _decorate_report(report)
            for report in ConfigurationReadinessManager.get_all_reports()
        ]

        status_counts = {
            "ready": 0,
            "warning": 0,
            "blocked": 0,
        }
        for report in reports:
            status_counts[report["status_class"]] += 1

        return render_template(
            "configuration/index.html",
            reports=reports,
            status_counts=status_counts,
        )

    @app.route("/configuration/<machine_code>/<stage_code>/phase-defaults", methods=["POST"])
    def configuration_stage_phase_defaults(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        try:
            groups_added, phases_added = _initialize_standard_phase_master(
                context
            )
            flash(
                f"Standard phase master initialized. Groups added: {groups_added}; phase options added: {phases_added}.",
                "success",
            )
        except Exception as exc:
            flash(f"Phase master initialization failed: {exc}", "error")

        return redirect(machine_stage_url("/configuration", context=context))


    @app.route("/configuration/<machine_code>/<stage_code>/tag-requirements", methods=["POST"])
    def configuration_stage_tag_requirements_save(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        purposes = request.form.getlist("purpose")
        reason = (
            request.form.get("reason")
            or
            "Stage PLC tag requirement setup updated"
        )
        rows = []
        skipped_purposes = []
        stage_type = context.get("stage_type")
        for purpose in purposes:
            purpose_key = (purpose or "").strip().upper()
            if not purpose_key:
                continue
            if not StagePLCTagRequirementManager.is_purpose_allowed_for_stage(
                purpose_key,
                stage_type,
            ):
                skipped_purposes.append(purpose_key)
                continue
            rows.append(
                {
                    "purpose": purpose_key,
                    "label": request.form.get(f"label_{purpose_key}"),
                    "requirement_level": request.form.get(f"requirement_level_{purpose_key}"),
                    "expected_type": request.form.get(f"expected_type_{purpose_key}"),
                    "array_required": request.form.get(f"array_required_{purpose_key}"),
                    "minimum_array_size": request.form.get(f"minimum_array_size_{purpose_key}"),
                    "array_start_index": request.form.get(f"array_start_index_{purpose_key}"),
                    "array_end_index": request.form.get(f"array_end_index_{purpose_key}"),
                    "default_tag_name": request.form.get(f"default_tag_name_{purpose_key}"),
                    "search_hint": request.form.get(f"search_hint_{purpose_key}"),
                    "active": request.form.get(f"active_{purpose_key}"),
                    "display_order": request.form.get(f"display_order_{purpose_key}"),
                }
            )

        new_purpose = (request.form.get("new_purpose") or "").strip().upper()
        if new_purpose:
            if not StagePLCTagRequirementManager.is_purpose_allowed_for_stage(
                new_purpose,
                stage_type,
            ):
                skipped_purposes.append(new_purpose)
            else:
                rows.append(
                    {
                        "purpose": new_purpose,
                        "label": request.form.get("new_label"),
                        "requirement_level": request.form.get("new_requirement_level"),
                        "expected_type": request.form.get("new_expected_type"),
                        "array_required": request.form.get("new_array_required"),
                        "minimum_array_size": request.form.get("new_minimum_array_size"),
                        "array_start_index": request.form.get("new_array_start_index"),
                        "array_end_index": request.form.get("new_array_end_index"),
                        "default_tag_name": request.form.get("new_default_tag_name"),
                        "search_hint": request.form.get("new_search_hint"),
                        "active": request.form.get("new_active"),
                        "display_order": request.form.get("new_display_order"),
                    }
                )

        old_rows = StagePLCTagRequirementManager.get_stage_requirements(
            context["machine_id"],
            context["stage_id"],
            active_only=False,
        )

        success, errors = StagePLCTagRequirementManager.save_stage_requirements(
            context["machine_id"],
            context["stage_id"],
            rows,
        )

        if not success:
            for error in errors[:8]:
                flash(error, "error")
            return redirect(machine_stage_url("/configuration", context=context))

        try:
            new_rows = StagePLCTagRequirementManager.get_stage_requirements(
                context["machine_id"],
                context["stage_id"],
                active_only=False,
            )
            _audit_tag_requirement_changes(
                context,
                old_rows,
                new_rows,
                reason,
            )
            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action="PLC_TAG_REQUIREMENT_SETUP_UPDATED",
                change_source="CONFIGURATION_CENTER",
                record_id=context["stage_id"],
                old_value="stage_plc_tag_requirements",
                new_value=f"{len(rows)} rule(s) saved for {context['machine_code']} {context['stage_type']}",
                reason=reason,
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
            )
        except Exception:
            pass

        if skipped_purposes:
            flash(
                "Skipped wrong-stage phase purpose(s): "
                + ", ".join(sorted(set(skipped_purposes))),
                "warning",
            )
        flash("PLC tag setup rules saved for this machine/stage.", "success")
        return redirect(machine_stage_url("/configuration", context=context))

    @app.route("/configuration/<machine_code>/<stage_code>/tag-purpose-remap", methods=["POST"])
    def configuration_stage_tag_purpose_remap(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        tag_ids = request.form.getlist("tag_id")
        reason = (
            request.form.get("reason")
            or
            "PLC tag configuration updated from GUI"
        ).strip()

        if not reason:
            flash("Enter reason before saving PLC tag configuration.", "error")
            return redirect(machine_stage_url("/configuration", context=context))

        rows = []
        skipped_purposes = []
        stage_type = context.get("stage_type")
        for tag_id in tag_ids:
            try:
                tag_id_int = int(tag_id)
            except Exception:
                continue
            tag_purpose = (
                request.form.get(f"tag_purpose_{tag_id}")
                or
                ""
            ).strip().upper()
            if (
                tag_purpose
                and
                not StagePLCTagRequirementManager.is_purpose_allowed_for_stage(
                    tag_purpose,
                    stage_type,
                )
            ):
                skipped_purposes.append(tag_purpose)
                tag_purpose = ""

            rows.append({
                "id": tag_id_int,
                "tag_name": request.form.get(f"tag_name_{tag_id}"),
                "tag_type": request.form.get(f"tag_type_{tag_id}"),
                "is_array": request.form.get(f"is_array_{tag_id}", "0"),
                "array_size": request.form.get(f"array_size_{tag_id}"),
                "array_start_index": request.form.get(f"array_start_index_{tag_id}"),
                "array_end_index": request.form.get(f"array_end_index_{tag_id}"),
                "description": request.form.get(f"description_{tag_id}"),
                "tag_purpose": tag_purpose,
            })

        result = PLCTagManager.bulk_update_stage_tags(
            machine_id=context["machine_id"],
            stage_id=context["stage_id"],
            rows=rows,
        )

        if not result.get("success"):
            for error in result.get("errors", [])[:8]:
                flash(error, "error")
            return redirect(machine_stage_url("/configuration", context=context))

        _audit_plc_tag_bulk_changes(
            result.get("changes"),
            reason,
        )

        try:
            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action="PLC_TAG_CONFIGURATION_BULK_UPDATED",
                change_source="CONFIGURATION_CENTER",
                record_id=context["stage_id"],
                old_value="plc_tags",
                new_value=f"{len(result.get('changes') or [])} PLC tag row(s) changed for {context['machine_code']} {context['stage_type']}",
                reason=reason,
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
            )
        except Exception:
            pass

        if skipped_purposes:
            flash(
                "Cleared wrong-stage phase purpose assignment(s): "
                + ", ".join(sorted(set(skipped_purposes))),
                "warning",
            )
        flash(result.get("message") or "PLC tag configuration saved.", "success")
        return redirect(machine_stage_url("/configuration", context=context))



    @app.route("/configuration/<machine_code>/<stage_code>/plc-assignment", methods=["POST"])
    def configuration_stage_plc_assignment_save(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        plc_id = (request.form.get("plc_id") or "").strip()
        reason = (request.form.get("reason") or "").strip()

        if not plc_id:
            flash("Select an existing PLC to assign.", "error")
            return redirect(machine_stage_url("/configuration", context=context))

        if not reason:
            flash("Enter reason before changing PLC assignment.", "error")
            return redirect(machine_stage_url("/configuration", context=context))

        try:
            result = PLCRegistryManager.assign_existing_plc_to_stage(
                plc_id=plc_id,
                machine_stage_id=context["stage_id"],
            )

            old_plc = result.get("old") or {}
            new_plc = result.get("new") or {}

            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action="PLC_STAGE_ASSIGNMENT_CHANGED",
                change_source="CONFIGURATION_CENTER",
                plc_name=new_plc.get("plc_name"),
                record_id=new_plc.get("id"),
                old_value=json.dumps(
                    {
                        "machine_stage_id": old_plc.get("machine_stage_id"),
                        "stage_display": old_plc.get("stage_display"),
                        "active": old_plc.get("active"),
                    },
                    sort_keys=True,
                    default=str,
                ),
                new_value=json.dumps(
                    {
                        "machine_stage_id": new_plc.get("machine_stage_id"),
                        "stage_display": new_plc.get("stage_display"),
                        "active": new_plc.get("active"),
                    },
                    sort_keys=True,
                    default=str,
                ),
                reason=reason,
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
            )

            for replaced in result.get("deactivated") or []:
                try:
                    AuditManager.log_event(
                        username=session.get("username"),
                        role=session.get("role"),
                        action="PLC_STAGE_ASSIGNMENT_REPLACED",
                        change_source="CONFIGURATION_CENTER",
                        plc_name=replaced.get("plc_name"),
                        record_id=replaced.get("id"),
                        old_value="ACTIVE",
                        new_value="DISABLED",
                        reason=(
                            reason
                            + "; replaced by "
                            + str(new_plc.get("plc_name") or "selected PLC")
                        ),
                        user_agent=request.headers.get("User-Agent", ""),
                        forwarded_for=request.headers.get("X-Forwarded-For"),
                        request_host=request.host,
                    )
                except Exception:
                    pass

            old_stage = old_plc.get("stage_display") or "Unassigned stage"
            if result.get("moved_from_stage"):
                flash(
                    f"{new_plc.get('plc_name')} assigned to "
                    f"{context['machine_stage_display']}. Previous assignment: "
                    f"{old_stage}.",
                    "success",
                )
            elif result.get("activated"):
                flash(
                    f"{new_plc.get('plc_name')} activated for "
                    f"{context['machine_stage_display']}.",
                    "success",
                )
            else:
                flash(
                    f"{new_plc.get('plc_name')} confirmed as the active PLC for "
                    f"{context['machine_stage_display']}.",
                    "success",
                )

            replaced_count = len(result.get("deactivated") or [])
            if replaced_count:
                flash(
                    f"{replaced_count} previous active PLC assignment(s) for this "
                    "stage were disabled.",
                    "warning",
                )

        except ValueError as exc:
            flash(str(exc), "error")
        except Exception as exc:
            flash(f"PLC assignment could not be changed: {exc}", "error")

        return redirect(machine_stage_url("/configuration", context=context))


    @app.route("/configuration/<machine_code>/<stage_code>/plc-registry", methods=["POST"])
    def configuration_stage_plc_registry_save(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        reason = (
            request.form.get("reason")
            or
            ""
        ).strip()

        if not reason:
            flash("Enter reason before saving PLC communication setup.", "error")
            return redirect(machine_stage_url("/configuration", context=context))

        plc_id = (
            request.form.get("plc_id")
            or
            ""
        ).strip()

        try:
            result = PLCRegistryManager.save_stage_plc_config(
                plc_id=plc_id if plc_id else None,
                machine_stage_id=context["stage_id"],
                plc_name=request.form.get("plc_name"),
                ip_address=request.form.get("ip_address"),
                controller_type=request.form.get("controller_type"),
                firmware_revision=request.form.get("firmware_revision"),
                program_revision=request.form.get("program_revision"),
                processor_name=request.form.get("processor_name"),
                plc_software=request.form.get("plc_software"),
                description=request.form.get("description"),
                active=request.form.get("active", "0"),
                created_by=session.get("username"),
            )

            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action=(
                    "PLC_REGISTRY_CREATED"
                    if result.get("created")
                    else
                    "PLC_REGISTRY_UPDATED"
                ),
                change_source="CONFIGURATION_CENTER",
                plc_name=(result.get("new") or {}).get("plc_name"),
                record_id=(result.get("new") or {}).get("id"),
                old_value=json.dumps(
                    result.get("old"),
                    sort_keys=True,
                    default=str,
                ),
                new_value=json.dumps(
                    result.get("new"),
                    sort_keys=True,
                    default=str,
                ),
                reason=reason,
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
            )

            flash(
                "PLC communication setup saved for this machine/stage.",
                "success",
            )

        except ValueError as exc:
            flash(str(exc), "error")
        except Exception as exc:
            flash(f"PLC communication setup could not be saved: {exc}", "error")

        return redirect(machine_stage_url("/configuration", context=context))

    @app.route("/configuration/<machine_code>/<stage_code>/seed-plc-tags", methods=["POST"])
    def configuration_stage_seed_plc_tags(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        reason = (
            request.form.get("reason")
            or
            ""
        ).strip()

        if not reason:
            flash("Enter reason before creating missing PLC tag rows.", "error")
            return redirect(machine_stage_url("/configuration", context=context))

        include_recommended = request.form.get("include_recommended", "1") == "1"

        result = PLCTagManager.create_missing_tags_from_requirements(
            machine_id=context["machine_id"],
            stage_id=context["stage_id"],
            username=session.get("username"),
            include_recommended=include_recommended,
        )

        if not result.get("success"):
            for error in result.get("errors", [])[:8]:
                flash(error, "error")
            return redirect(machine_stage_url("/configuration", context=context))

        created = result.get("created") or []
        skipped = result.get("skipped") or []

        try:
            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action="PLC_TAG_ROWS_CREATED_FROM_SETUP_RULES",
                change_source="CONFIGURATION_CENTER",
                record_id=context["stage_id"],
                old_value=json.dumps(
                    {
                        "machine": context.get("machine_code"),
                        "stage": context.get("stage_type"),
                        "skipped": skipped,
                    },
                    sort_keys=True,
                    default=str,
                ),
                new_value=json.dumps(
                    {
                        "created_count": len(created),
                        "created": created,
                    },
                    sort_keys=True,
                    default=str,
                ),
                reason=reason,
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
            )
        except Exception:
            pass

        if created:
            flash(
                f"{len(created)} missing PLC tag row(s) created from active setup rules. You can now edit/rename/remap them below.",
                "success",
            )
        else:
            flash(
                "No missing PLC tag rows were created. Existing purpose mappings are already present.",
                "info",
            )

        if skipped:
            flash(
                f"{len(skipped)} setup rule(s) already had mapped PLC tags and were skipped.",
                "info",
            )

        return redirect(machine_stage_url("/configuration", context=context))



    @app.route("/configuration/<machine_code>/<stage_code>")
    def configuration_stage(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        report = ConfigurationReadinessManager.get_report(
            context["machine_id"],
            context["stage_id"],
        )
        if not report:
            flash("Configuration report could not be built.", "error")
            return redirect("/configuration")

        return render_template(
            "configuration/stage_readiness.html",
            report=_decorate_report(report),
            back_url="/configuration",
        )
