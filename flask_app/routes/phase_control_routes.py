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
from flask_app.security.role_guard import role_can
from flask_app.stage_url_helper import (
    add_machine_stage_url_fields,
    get_machine_stage_context_by_code,
    machine_stage_url,
)


SECOND_STAGE_DEFAULT_GROUPS = [
    ("CAP_STRIP_SIDE", "Cap Strip Side", "Cap strip side phase-control group", 1),
    ("BT_SIDE", "B&T Side", "Belt and tread side phase-control group", 2),
    ("SHAPING_SIDE", "Shaping Side", "Shaping side phase-control group", 3),
]

FIRST_STAGE_DEFAULT_GROUPS = [
    ("APPLICATION_SIDE", "Application Side", "First stage application side phase-control group", 1),
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
    "SHAPING_SIDE": [
        "Carcass Loader",
        "Preshaping",
        "Stitching Cycle",
        "Remove Cycle",
        "Empty Phase",
    ],
}

FIRST_STAGE_DEFAULT_PHASES = {
    "APPLICATION_SIDE": [
        "IL With Toproll",
        "IL Without Toproll",
        "Ply 1 With Toproll",
        "Ply 1 Without Toproll",
        "Ply 2 With Toproll",
        "Ply 2 Without Toproll",
        "Ply 3 With Toproll",
        "Ply 3 Without Toproll",
        "Sidewall With Stitcher",
        "Sidewall Without Stitcher",
        "RRD With Contour Stitcher",
        "RRD With Contour & Disk Stitcher",
        "RRD With Disk Stitcher",
        "Insert Beads",
        "Set Beads",
        "Turnup Ring",
        "Contour Stitcher",
        "Material 1 Manual",
        "Disk Stitcher",
        "Material 2 Manual",
        "Empty Phase",
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


def _phase_groups(machine_stage_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM phase_control_group_master
        WHERE machine_stage_id = ?
        ORDER BY
            display_order,
            phase_group_name
        """,
        (machine_stage_id,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def _phase_options(machine_stage_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM phase_control_master
        WHERE machine_stage_id = ?
        ORDER BY
            CASE COALESCE(phase_group_code, 'MAIN')
                WHEN 'APPLICATION_SIDE' THEN 1
                WHEN 'CAP_STRIP_SIDE' THEN 1
                WHEN 'BT_SIDE' THEN 2
                WHEN 'SHAPING_SIDE' THEN 3
                WHEN 'MAIN' THEN 9
                ELSE 99
            END,
            display_order,
            phase_control_name
        """,
        (machine_stage_id,)
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
    cursor.execute(
        """
        SELECT id
        FROM phase_control_master
        WHERE machine_stage_id = ?
            AND UPPER(COALESCE(phase_group_code, 'MAIN')) = UPPER(?)
            AND UPPER(phase_control_name) = UPPER(?)
        """,
        (
            context["stage_id"],
            group_code,
            phase_name,
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
            description,
            display_order,
            active,
            machine_stage_id,
            phase_group_code,
            phase_group_name
        )
        VALUES (?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            context["stage_type"],
            phase_name,
            description,
            display_order,
            context["stage_id"],
            group_code,
            group_name,
        )
    )
    return True


def _initialize_standard_phase_master(context):
    stage_type = str(context.get("stage_type") or "").upper()
    groups = SECOND_STAGE_DEFAULT_GROUPS
    phases = SECOND_STAGE_DEFAULT_PHASES

    if stage_type == "FIRST_STAGE":
        groups = FIRST_STAGE_DEFAULT_GROUPS
        phases = FIRST_STAGE_DEFAULT_PHASES

    conn = get_connection()
    cursor = conn.cursor()
    inserted_groups = 0
    inserted_phases = 0

    for group_code, group_name, description, display_order in groups:
        if _insert_group_if_missing(
            cursor,
            context,
            group_code,
            group_name,
            description,
            display_order,
        ):
            inserted_groups += 1

        for index, phase_name in enumerate(phases.get(group_code, []), start=1):
            if _insert_phase_if_missing(
                cursor,
                context,
                group_code,
                group_name,
                phase_name,
                phase_name,
                index,
            ):
                inserted_phases += 1

    conn.commit()
    conn.close()

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
    groups = _phase_groups(context["stage_id"])
    group_by_code = {
        group["phase_group_code"]: group
        for group in groups
    }

    group_code = (request.form.get("phase_group_code") or "").strip()
    phase_name = (request.form.get("phase_control_name") or "").strip()
    description = (request.form.get("description") or phase_name).strip()
    display_order = request.form.get("display_order", type=int) or 0

    if group_code not in group_by_code:
        flash("Select a valid phase group before adding a phase.", "error")
        return

    if not phase_name:
        flash("Phase name is required.", "error")
        return

    group = group_by_code[group_code]
    conn = get_connection()
    cursor = conn.cursor()
    inserted = _insert_phase_if_missing(
        cursor,
        context,
        group_code,
        group["phase_group_name"],
        phase_name,
        description,
        display_order,
    )
    conn.commit()
    conn.close()

    if inserted:
        AuditManager.log_event(
            username=session.get("username"),
            role=session.get("role"),
            action="PHASE_CONTROL_MASTER_CREATED",
            change_source="WEB_PHASE_MASTER",
            record_id=str(context["stage_id"]),
            new_value=f"{group_code} - {phase_name}",
            reason=context.get("machine_stage_display")
        )
        flash("Phase option created.", "success")
    else:
        flash("Phase option already exists in this group.", "warning")


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
            else:
                flash("Unknown phase master action.", "error")

            return redirect(canonical_url)

        groups = _phase_groups(context["stage_id"])
        options = _phase_options(context["stage_id"])

        return render_template(
            "phase_controls/stage_master.html",
            context=context,
            groups=groups,
            options=options,
            grouped_options=_phase_options_by_group(groups, options),
            back_url="/phase-controls"
        )
