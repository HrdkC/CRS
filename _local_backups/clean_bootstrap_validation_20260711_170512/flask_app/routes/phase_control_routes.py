import re

from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
)

from database.audit_manager import AuditManager
from database.database import get_connection
from database.phase_control_default_manager import PhaseControlDefaultManager
from database.phase_template_manager import PhaseTemplateManager
from flask_app.security.role_guard import role_can
from flask_app.stage_url_helper import (
    add_machine_stage_url_fields,
    get_machine_stage_context_by_code,
    machine_stage_url,
)


SECOND_STAGE_DEFAULT_GROUPS = [
    ("CAP_STRIP_SIDE", "Cap Strip Side", "Cap strip side phase-control group", 1),
    ("BT_SIDE", "B&T Side", "Belt and tread side phase-control group", 2),
]

FIRST_STAGE_DEFAULT_GROUPS = [
    ("MAIN", "Phase Control", "First stage single phase-control group", 1),
]

SECOND_STAGE_DEFAULT_PHASES = {
    "CAP_STRIP_SIDE": [
        "Apply CapStrip",
        "Apply Tread",
        "Empty Phase",
    ],
    "BT_SIDE": [
        "Apply Belt 1",
        "Apply Belt 2",
        "Turn Table",
        "Apply Tread",
        "Remove Belt Package",
        "Empty Phase",
    ],
}

FIRST_STAGE_DEFAULT_PHASES = {
    "MAIN": [
        "INNERLINER WITH TOPROLL",
        "INNERLINER WITHOUT TOPROLL",
        "PLY 1 WITH TOPROLL",
        "PLY 1 WITHOUT TOPROLL",
        "PLY 2 WITH TOPROLL",
        "PLY 2 WITHOUT TOPROLL",
        "SIDEWALL WITHOUT STITCHER WITH TOPROLL",
        "SIDEWALL WITHOUT STITCHER",
        "RRD WITH CONTOUR STITCHER",
        "RRD WITH CONTOUR & DISK STITCHER",
        "RRD WITH DISK STITCHER",
        "INSERT BEADS",
        "SET BEADS",
        "TURNUPRING",
        "CONTOUR STITCHER",
        "DISK STITCHER",
        "MATERIAL 1 MANUAL",
        "MATERIAL 2 MANUAL",
        "REINFORCEMENT MATERIAL",
        "PLY 3 WITH TOPROLL",
        "PLY 3 WITHOUT TOPROLL",
        "EMPTY PHASE",
    ],
}


def _engineering_config_allowed():
    return (
        session.get("logged_in")
        and
        role_can(
            session.get("role"),
            "engineering_config"
        )
    )


def _normalize_code(value):
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def _is_first_stage(stage_type):
    return (
        str(stage_type or "").strip().upper().replace(" ", "_")
        in {"FIRST_STAGE", "FIRSTSTAGE", "FS"}
    )


def _is_second_stage(stage_type):
    return (
        str(stage_type or "").strip().upper().replace(" ", "_")
        in {"SECOND_STAGE", "SECONDSTAGE", "SS"}
    )


def _stage_targets():
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
            s.description AS stage_description,
            (
                SELECT COUNT(*)
                FROM phase_control_group_master g
                WHERE g.machine_stage_id = s.id
                    AND COALESCE(g.active, 1) = 1
            ) AS phase_group_count,
            (
                SELECT COUNT(*)
                FROM phase_control_master p
                WHERE p.machine_stage_id = s.id
                    AND COALESCE(p.active, 1) = 1
            ) AS phase_count
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
        row["phase_master_url"] = machine_stage_url(
            "/phase-controls",
            context=row
        )

    return rows


def _phase_groups(machine_stage_id, stage_type=None, include_inactive=False):
    conditions = ["machine_stage_id = ?"]
    params = [machine_stage_id]
    if not include_inactive:
        conditions.append("COALESCE(active, 1) = 1")
    if _is_first_stage(stage_type):
        conditions.append("UPPER(COALESCE(phase_group_code, 'MAIN')) = 'MAIN'")
    elif _is_second_stage(stage_type):
        conditions.append(
            "UPPER(COALESCE(phase_group_code, 'MAIN')) "
            "IN ('CAP_STRIP_SIDE', 'BT_SIDE')"
        )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT *
        FROM phase_control_group_master
        WHERE {" AND ".join(conditions)}
        ORDER BY
            display_order,
            phase_group_name
        """,
        tuple(params)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def _phase_options(machine_stage_id, stage_type=None, include_inactive=False):
    PhaseTemplateManager.ensure_schema()
    PhaseTemplateManager.sync_phase_keys(machine_stage_id)

    conditions = ["machine_stage_id = ?"]
    params = [machine_stage_id]
    if not include_inactive:
        conditions.append("COALESCE(active, 1) = 1")
    if _is_first_stage(stage_type):
        conditions.append("UPPER(COALESCE(phase_group_code, 'MAIN')) = 'MAIN'")
    elif _is_second_stage(stage_type):
        conditions.append(
            "UPPER(COALESCE(phase_group_code, 'MAIN')) "
            "IN ('CAP_STRIP_SIDE', 'BT_SIDE')"
        )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT *
        FROM phase_control_master
        WHERE {" AND ".join(conditions)}
        ORDER BY
            CASE COALESCE(phase_group_code, 'MAIN')
                WHEN 'MAIN' THEN 0
                WHEN 'CAP_STRIP_SIDE' THEN 1
                WHEN 'BT_SIDE' THEN 2
                ELSE 99
            END,
            display_order,
            phase_control_name
        """,
        tuple(params)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def _phase_options_by_group(groups, options):
    grouped = []
    for group in groups:
        group_code = group.get("phase_group_code")
        grouped.append({
            "group": group,
            "options": [
                option
                for option in options
                if (option.get("phase_group_code") or "MAIN") == group_code
            ],
        })
    return grouped


def _insert_group_if_missing(cursor, context, group_code, group_name, description, display_order):
    cursor.execute(
        """
        SELECT id
        FROM phase_control_group_master
        WHERE machine_stage_id = ?
            AND UPPER(phase_group_code) = UPPER(?)
        """,
        (
            context["stage_id"],
            group_code,
        )
    )
    if cursor.fetchone():
        return False

    cursor.execute(
        """
        INSERT INTO phase_control_group_master
        (
            machine_stage_id,
            stage_type,
            phase_group_code,
            phase_group_name,
            description,
            display_order,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (
            context["stage_id"],
            context["stage_type"],
            group_code,
            group_name,
            description,
            display_order,
        )
    )
    return True


def _insert_phase_if_missing(cursor, context, group_code, group_name, phase_name, description, display_order):
    clean_name = PhaseTemplateManager.clean_display_name(phase_name)
    phase_key = PhaseTemplateManager.phase_key(clean_name)
    plc_phase_code = PhaseTemplateManager._phase_code_from_name(
        group_code,
        clean_name,
        display_order,
    )

    cursor.execute(
        """
        SELECT id
        FROM phase_control_master
        WHERE machine_stage_id = ?
            AND UPPER(COALESCE(phase_group_code, 'MAIN')) = UPPER(?)
            AND UPPER(COALESCE(phase_control_key, phase_control_name)) = UPPER(?)
        """,
        (
            context["stage_id"],
            group_code,
            phase_key,
        )
    )
    if cursor.fetchone():
        return False

    cursor.execute(
        """
        INSERT INTO phase_control_master
        (
            stage_type,
            phase_control_name,
            phase_control_key,
            plc_phase_code,
            description,
            display_order,
            active,
            machine_stage_id,
            phase_group_code,
            phase_group_name
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            context["stage_type"],
            clean_name,
            phase_key,
            plc_phase_code,
            description,
            display_order,
            context["stage_id"],
            group_code,
            group_name,
        )
    )
    return True


def _initialize_standard_phase_master(context):
    result = PhaseControlDefaultManager.initialize_for_context(context)
    inserted_groups = result.get("groups_added", 0)
    inserted_phases = result.get("phases_added", 0)

    AuditManager.log_event(
        username=session.get("username"),
        role=session.get("role"),
        action="PHASE_MASTER_DEFAULTS_INITIALIZED",
        change_source="WEB_PHASE_MASTER",
        record_id=str(context["stage_id"]),
        new_value=f"groups={inserted_groups}; phases={inserted_phases}",
        reason=context.get("machine_stage_display")
    )

    return inserted_groups, inserted_phases


def _create_group(context):
    if _is_first_stage(context.get("stage_type")):
        flash("First stage uses one Phase Control group only.", "warning")
        return

    group_name = (request.form.get("phase_group_name") or "").strip()
    group_code = _normalize_code(
        request.form.get("phase_group_code")
        or
        group_name
    )
    description = (request.form.get("description") or "").strip()
    display_order = request.form.get("display_order", type=int) or 0

    if not group_code or not group_name:
        flash("Phase group code and name are required.", "error")
        return

    conn = get_connection()
    cursor = conn.cursor()
    inserted = _insert_group_if_missing(
        cursor,
        context,
        group_code,
        group_name,
        description,
        display_order,
    )
    conn.commit()
    conn.close()

    if inserted:
        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PHASE_GROUP_CREATED",
            change_source="WEB_PHASE_MASTER",
            record_id=str(context["stage_id"]),
            new_value=f"{group_code} - {group_name}",
            reason=context.get("machine_stage_display")
        )
        flash("Phase group created.", "success")
    else:
        flash("Phase group already exists for this machine/stage.", "warning")


def _create_phase(context):
    groups = _phase_groups(context["stage_id"], context.get("stage_type"))
    group_by_code = {
        group["phase_group_code"]: group
        for group in groups
    }

    group_code = (request.form.get("phase_group_code") or "").strip()
    phase_name = (request.form.get("phase_control_name") or "").strip()
    description = (request.form.get("description") or phase_name).strip()
    display_order = request.form.get("display_order", type=int) or 0
    plc_phase_code = (request.form.get("plc_phase_code") or "").strip()

    if group_code not in group_by_code:
        flash("Select a valid phase group before adding a phase.", "error")
        return

    if not phase_name:
        flash("Phase name is required.", "error")
        return

    group = group_by_code[group_code]
    success, message, phase_id = PhaseTemplateManager.create_phase(
        machine_stage_id=context["stage_id"],
        stage_type=context["stage_type"],
        group_code=group_code,
        group_name=group["phase_group_name"],
        phase_name=phase_name,
        description=description,
        display_order=display_order,
        plc_phase_code=plc_phase_code if plc_phase_code else None,
    )

    if success:
        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PHASE_CONTROL_MASTER_CREATED",
            change_source="WEB_PHASE_MASTER",
            record_id=str(phase_id or context["stage_id"]),
            new_value=f"{group_code} - {PhaseTemplateManager.clean_display_name(phase_name)}",
            reason=context.get("machine_stage_display")
        )
        flash(message, "success")
    else:
        flash(message, "error")


def _save_phase_template(context):
    phase_ids = request.form.getlist("phase_id")
    remove_phase_ids = set()
    for value in request.form.getlist("remove_phase_id"):
        try:
            remove_phase_ids.add(str(int(value)))
        except Exception:
            continue
    reason = (
        request.form.get("reason")
        or
        "Stage-wise phase template updated"
    ).strip()

    protected_remove_ids = set()
    if remove_phase_ids:
        placeholders = ",".join("?" for _ in remove_phase_ids)
        conn = get_connection()
        cursor = conn.cursor()
        protected_rows = cursor.execute(
            f"""
            SELECT id
            FROM phase_control_master
            WHERE machine_stage_id = ?
                AND id IN ({placeholders})
                AND UPPER(COALESCE(phase_control_key, phase_control_name)) = 'EMPTY PHASE'
            """,
            tuple([context["stage_id"]] + [int(value) for value in remove_phase_ids])
        ).fetchall()
        conn.close()
        protected_remove_ids = {str(row["id"]) for row in protected_rows}

        if protected_remove_ids:
            flash(
                "Empty Phase is a required safe placeholder and cannot be removed.",
                "warning"
            )
            remove_phase_ids = remove_phase_ids - protected_remove_ids

    rows = []
    for phase_id in phase_ids:
        try:
            phase_id_int = int(phase_id)
        except Exception:
            continue

        rows.append(
            {
                "id": phase_id_int,
                "phase_group_code": request.form.get(f"phase_group_code_{phase_id}"),
                "phase_control_name": request.form.get(f"phase_control_name_{phase_id}"),
                "plc_phase_code": request.form.get(f"plc_phase_code_{phase_id}"),
                "description": request.form.get(f"description_{phase_id}"),
                "display_order": request.form.get(f"display_order_{phase_id}"),
                "active": (
                    0
                    if phase_id in remove_phase_ids
                    else 1 if request.form.get(f"active_{phase_id}") == "1" else 0
                ),
            }
        )

    success, errors, changed_count = PhaseTemplateManager.save_phase_rows(
        context["stage_id"],
        rows,
    )

    if not success:
        for error in errors[:8]:
            flash(error, "error")
        return

    try:
        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PHASE_TEMPLATE_MASTER_UPDATED",
            change_source="WEB_PHASE_MASTER",
            record_id=str(context["stage_id"]),
            new_value=(
                f"{changed_count} phase option(s) changed; "
                f"{len(remove_phase_ids)} removed from active dropdowns"
            ),
            reason=reason,
            user_agent=request.headers.get("User-Agent", ""),
            forwarded_for=request.headers.get("X-Forwarded-For"),
            request_host=request.host,
        )
    except Exception:
        pass

    if remove_phase_ids:
        flash(
            f"Phase template saved. {len(remove_phase_ids)} option(s) removed from recipe dropdowns.",
            "success"
        )
    else:
        flash(f"Phase template saved. {changed_count} phase option(s) updated.", "success")


def _save_group_template_text(context):
    groups = _phase_groups(context["stage_id"], context.get("stage_type"))
    group_by_code = {
        group["phase_group_code"]: group
        for group in groups
    }

    group_code = (request.form.get("phase_group_code") or "").strip()
    if group_code not in group_by_code:
        flash("Select a valid phase group for the pasted template.", "error")
        return

    template_text = request.form.get("phase_template_text") or ""
    deactivate_missing = request.form.get("deactivate_missing") == "1"
    reason = (
        request.form.get("reason")
        or
        "Stage-wise pasted phase template saved"
    ).strip()
    lines = template_text.splitlines()
    group = group_by_code[group_code]

    success, errors, result = PhaseTemplateManager.save_group_template_lines(
        machine_stage_id=context["stage_id"],
        stage_type=context["stage_type"],
        group_code=group_code,
        group_name=group["phase_group_name"],
        lines=lines,
        deactivate_missing=deactivate_missing,
    )

    if not success:
        for error in errors[:8]:
            flash(error, "error")
        return

    try:
        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PHASE_TEMPLATE_TEXT_SAVED",
            change_source="WEB_PHASE_MASTER",
            record_id=str(context["stage_id"]),
            parameter_name=group_code,
            new_value=(
                f"updated={result.get('updated', 0)}; "
                f"inserted={result.get('inserted', 0)}; "
                f"deactivated={result.get('deactivated', 0)}"
            ),
            reason=reason,
            user_agent=request.headers.get("User-Agent", ""),
            forwarded_for=request.headers.get("X-Forwarded-For"),
            request_host=request.host,
        )
    except Exception:
        pass

    flash(
        "Pasted phase template saved. "
        f"Updated {result.get('updated', 0)}, inserted {result.get('inserted', 0)}, "
        f"deactivated {result.get('deactivated', 0)}.",
        "success"
    )


def _cleanup_phase_duplicates(context):
    reason = (
        request.form.get("reason")
        or
        "Case-insensitive duplicate phase names merged"
    ).strip()
    success, errors, result = PhaseTemplateManager.merge_case_duplicates(
        context["stage_id"]
    )

    if not success:
        for error in errors[:8]:
            flash(error, "error")
        return

    try:
        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PHASE_TEMPLATE_DUPLICATES_MERGED",
            change_source="WEB_PHASE_MASTER",
            record_id=str(context["stage_id"]),
            new_value=(
                f"recipe_rows_remapped={result.get('merged', 0)}; "
                f"duplicates_deactivated={result.get('deactivated', 0)}"
            ),
            reason=reason,
            user_agent=request.headers.get("User-Agent", ""),
            forwarded_for=request.headers.get("X-Forwarded-For"),
            request_host=request.host,
        )
    except Exception:
        pass

    flash(
        "Duplicate phase names merged. "
        f"Recipe rows remapped: {result.get('merged', 0)}; "
        f"duplicate master rows deactivated: {result.get('deactivated', 0)}.",
        "success"
    )


def register_phase_control_routes(app):

    @app.route("/phase-controls")
    def phase_control_master():
        if not _engineering_config_allowed():
            return redirect("/")

        return render_template(
            "phase_controls/master.html",
            targets=_stage_targets()
        )

    @app.route(
        "/phase-controls/<machine_code>/<stage_code>",
        methods=["GET", "POST"]
    )
    def phase_control_master_stage(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True
        )

        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/phase-controls")

        canonical_url = machine_stage_url(
            "/phase-controls",
            context=context
        )
        current_path = f"/phase-controls/{machine_code}/{stage_code}"
        if request.method == "GET" and current_path != canonical_url:
            return redirect(canonical_url)

        if request.method == "POST":
            action = request.form.get("action")
            if action == "initialize_defaults":
                groups_added, phases_added = _initialize_standard_phase_master(
                    context
                )
                flash(
                    f"Standard phase master initialized. Groups added: {groups_added}; phases added: {phases_added}.",
                    "success"
                )
            elif action == "create_group":
                _create_group(context)
            elif action == "create_phase":
                _create_phase(context)
            elif action == "save_phase_template":
                _save_phase_template(context)
            elif action == "save_group_template_text":
                _save_group_template_text(context)
            elif action == "cleanup_duplicates":
                _cleanup_phase_duplicates(context)
            else:
                flash("Unknown phase master action.", "error")

            return redirect(canonical_url)

        PhaseTemplateManager.ensure_schema()
        existing_group_count = len(_phase_groups(
            context["stage_id"],
            context.get("stage_type"),
            include_inactive=True,
        ))
        existing_option_count = len(_phase_options(
            context["stage_id"],
            context.get("stage_type"),
            include_inactive=True,
        ))
        if existing_group_count == 0 and existing_option_count == 0:
            PhaseControlDefaultManager.initialize_for_context(context)
        PhaseTemplateManager.sync_phase_keys(context["stage_id"])

        groups = _phase_groups(
            context["stage_id"],
            context.get("stage_type"),
        )
        options = _phase_options(
            context["stage_id"],
            context.get("stage_type"),
            include_inactive=True,
        )
        display_options = _phase_options(
            context["stage_id"],
            context.get("stage_type"),
        )
        duplicate_report = PhaseTemplateManager.get_duplicate_report(
            context["stage_id"]
        )

        return render_template(
            "phase_controls/stage_master.html",
            context=context,
            groups=groups,
            options=options,
            grouped_options=_phase_options_by_group(groups, display_options),
            duplicate_report=duplicate_report,
            back_url="/phase-controls"
        )
