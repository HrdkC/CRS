from flask import (
    redirect,
    render_template,
    session
)

from database.database import (
    get_connection
)

from helper.datetime_helper import utc_to_ist
from flask_app.security.role_guard import (
    normalize_role,
    role_can
)


def _safe_count(cursor, query, params=()):

    try:

        cursor.execute(
            query,
            params
        )

        return cursor.fetchone()[0]

    except Exception:

        return 0


def _safe_rows(cursor, query, params=()):

    try:

        cursor.execute(
            query,
            params
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    except Exception:

        return []


def _percent(count, total):

    try:
        total = int(total or 0)
        count = int(count or 0)
        if total <= 0:
            return 0
        return min(100, round((count / total) * 100))
    except Exception:
        return 0


def _build_recipe_lifecycle(cursor):

    rows = _safe_rows(
        cursor,
        """
        SELECT UPPER(COALESCE(status, 'UNKNOWN')) AS status, COUNT(*) AS count
        FROM recipes
        WHERE COALESCE(is_test_only, 0) = 0
        GROUP BY UPPER(COALESCE(status, 'UNKNOWN'))
        """
    )
    counts = {
        row["status"]: int(row["count"] or 0)
        for row in rows
    }
    total = sum(counts.values())

    lifecycle = [
        ("DRAFT", "Draft", "status-warning"),
        ("REVIEW", "Review", "status-info"),
        ("APPROVED", "Approved", "status-neutral"),
        ("RELEASED", "Released", "status-success"),
        ("REJECTED", "Rejected", "status-danger"),
    ]

    return [
        {
            "key": key,
            "label": label,
            "count": counts.get(key, 0),
            "percent": _percent(counts.get(key, 0), total),
            "status_class": status_class,
        }
        for key, label, status_class in lifecycle
    ]


def _build_stage_readiness(cursor):

    rows = _safe_rows(
        cursor,
        """
        SELECT
            m.machine_code,
            s.stage_type,
            s.id AS stage_id,
            (
                SELECT COUNT(*)
                FROM plc_registry pr
                WHERE pr.machine_stage_id = s.id
                    AND COALESCE(pr.active, 1) = 1
            ) AS active_plcs,
            (
                SELECT COUNT(*)
                FROM parameter_definitions pd
                WHERE pd.machine_id = m.id
                    AND pd.stage_id = s.id
                    AND COALESCE(pd.used, 1) = 1
            ) AS used_parameters,
            (
                SELECT COUNT(*)
                FROM parameter_definitions pd
                WHERE pd.machine_id = m.id
                    AND pd.stage_id = s.id
                    AND COALESCE(pd.used, 1) = 0
            ) AS unused_parameters,
            (
                SELECT COUNT(*)
                FROM phase_control_group_master pg
                WHERE pg.machine_stage_id = s.id
                    AND COALESCE(pg.active, 1) = 1
            ) AS phase_groups,
            (
                SELECT COUNT(*)
                FROM phase_control_master pm
                WHERE pm.machine_stage_id = s.id
                    AND COALESCE(pm.active, 1) = 1
            ) AS phase_options,
            (
                SELECT COUNT(*)
                FROM recipes r
                WHERE r.machine_id = m.id
                    AND r.stage_id = s.id
                    AND r.status = 'RELEASED'
                    AND COALESCE(r.is_test_only, 0) = 0
            ) AS released_recipes
        FROM tbm_machines m
        INNER JOIN machine_stages s
            ON s.machine_id = m.id
        WHERE COALESCE(m.active, 1) = 1
            AND COALESCE(s.active, 1) = 1
        ORDER BY
            m.machine_code,
            CASE UPPER(s.stage_type)
                WHEN 'FIRST_STAGE' THEN 1
                WHEN 'SECOND_STAGE' THEN 2
                ELSE 99
            END
        LIMIT 10
        """
    )

    readiness = []
    for row in rows:
        active_plcs = int(row.get("active_plcs") or 0)
        used_parameters = int(row.get("used_parameters") or 0)
        phase_groups = int(row.get("phase_groups") or 0)
        phase_options = int(row.get("phase_options") or 0)
        released_recipes = int(row.get("released_recipes") or 0)

        status = "OK"
        status_class = "status-success"
        if active_plcs == 0 or used_parameters == 0 or phase_groups == 0 or phase_options == 0:
            status = "Blocked"
            status_class = "status-danger"
        elif released_recipes == 0:
            status = "Warning"
            status_class = "status-warning"

        stage_code = "FS" if str(row.get("stage_type")).upper() == "FIRST_STAGE" else "SS"
        row["status"] = status
        row["status_class"] = status_class
        row["stage_code"] = stage_code
        row["configuration_url"] = f"/configuration/{row.get('machine_code')}/{stage_code}"
        row["recipe_url"] = f"/recipes/{row.get('machine_code')}/{stage_code}"
        readiness.append(row)

    return readiness


def _build_recent_activity(cursor):

    rows = _safe_rows(
        cursor,
        """
        SELECT
            timestamp,
            username,
            role,
            action,
            recipe_code,
            recipe_version,
            change_source
        FROM audit_log
        ORDER BY timestamp DESC, id DESC
        LIMIT 6
        """
    )

    for row in rows:
        row["timestamp_ist"] = utc_to_ist(row.get("timestamp"))
        if row.get("recipe_code") and row.get("recipe_version"):
            row["record_label"] = f"{row.get('recipe_code')} V{row.get('recipe_version')}"
        else:
            row["record_label"] = row.get("recipe_code") or "-"

    return rows


def _alert_is_accessible(role, href):

    normalized_role = normalize_role(role)

    if href.startswith("/recipes"):
        return role_can(normalized_role, "recipe_view")

    if href.startswith("/plcs"):
        return role_can(normalized_role, "engineering_config")

    if href.startswith("/audit-history"):
        return role_can(normalized_role, "audit_view")

    if href.startswith("/users"):
        return role_can(normalized_role, "user_manage")

    if href.startswith("/active-sessions"):
        return role_can(normalized_role, "session_manage")

    return True


def _build_dashboard_alerts(role, counts):

    normalized_role = normalize_role(
        role
    )

    alert_map = {
        "current_released": {
            "label": "Current Production",
            "count": counts["current_released_count"],
            "detail": "Released recipes available for PLC buffer operations",
            "href": "/recipes/P15/FS",
            "status_class": "status-success"
        },
        "draft": {
            "label": "Draft Recipes",
            "count": counts["draft_count"],
            "detail": "Recipes still under production preparation",
            "href": "/recipes/P15/FS",
            "status_class": "status-warning"
        },
        "review": {
            "label": "Pending Review",
            "count": counts["review_count"],
            "detail": "Recipes waiting for Technology/Admin decision",
            "href": "/recipes/P15/FS",
            "status_class": "status-info"
        },
        "plc_blocked": {
            "label": "PLC Operation Blocks",
            "count": counts["blocked_operation_count"],
            "detail": "Recent blocked PLC buffer operation jobs",
            "href": "/audit-history",
            "status_class": "status-danger"
        },
        "incomplete": {
            "label": "Incomplete Recipes",
            "count": counts["incomplete_recipe_count"],
            "detail": "Recipes missing parameters or phase-control rows",
            "href": "/recipes",
            "status_class": "status-danger"
        },
        "tag_typo": {
            "label": "PLC Tag Cleanup",
            "count": counts["plc_tag_typo_count"],
            "detail": "Legacy CSR download-complete tag names found",
            "href": "/plcs",
            "status_class": "status-warning"
        },
        "test_only": {
            "label": "Test Only Recipes",
            "count": counts["test_only_recipe_count"],
            "detail": "Non-production recipes kept for trial/reference use",
            "href": "/recipes",
            "status_class": "status-neutral"
        }
    }

    role_alert_keys = {
        "ADMIN": [
            "review",
            "plc_blocked",
            "incomplete",
            "tag_typo",
            "test_only",
            "current_released"
        ],
        "ENGINEERING": [
            "plc_blocked",
            "incomplete",
            "tag_typo",
            "test_only",
            "current_released"
        ],
        "TECHNOLOGY": [
            "review",
            "draft",
            "current_released"
        ],
        "PRODUCTION": [
            "draft",
            "review",
            "current_released"
        ],
        "EDITOR": [
            "draft",
            "review",
            "current_released"
        ],
        "OPERATOR": [
            "current_released"
        ],
        "VIEWER": [
            "current_released"
        ]
    }

    alerts = []

    for key in role_alert_keys.get(normalized_role, ["current_released"]):
        alert = alert_map[key]
        if _alert_is_accessible(normalized_role, alert["href"]):
            alerts.append(alert)

    return alerts


def register_dashboard_routes(app):

    @app.route("/")
    def dashboard():

        if not session.get("logged_in"):

            return redirect("/login")

        conn = get_connection()
        cursor = conn.cursor()

        family_count = _safe_count(
            cursor,
            "SELECT COUNT(*) FROM tbm_families"
        )
        recipe_count = _safe_count(
            cursor,
            "SELECT COUNT(*) FROM recipes"
        )
        plc_count = _safe_count(
            cursor,
            "SELECT COUNT(*) FROM plc_master"
        )
        configured_plc_count = _safe_count(
            cursor,
            "SELECT COUNT(*) FROM plc_registry"
        )
        machine_count = _safe_count(
            cursor,
            "SELECT COUNT(*) FROM tbm_machines"
        )
        stage_count = _safe_count(
            cursor,
            "SELECT COUNT(*) FROM machine_stages"
        )
        user_count = _safe_count(
            cursor,
            "SELECT COUNT(*) FROM users"
        )

        dashboard_counts = {
            "current_released_count": _safe_count(
                cursor,
                """
                SELECT COUNT(*)
                FROM recipes r
                WHERE COALESCE(r.is_test_only, 0) = 0
                AND r.status = 'RELEASED'
                AND r.version = (
                    SELECT MAX(x.version)
                    FROM recipes x
                    WHERE x.machine_id = r.machine_id
                    AND x.stage_id = r.stage_id
                    AND UPPER(x.recipe_code) = UPPER(r.recipe_code)
                    AND x.status = 'RELEASED'
                )
                """
            ),
            "draft_count": _safe_count(
                cursor,
                """
                SELECT COUNT(*)
                FROM recipes
                WHERE status = 'DRAFT'
                AND COALESCE(is_test_only, 0) = 0
                """
            ),
            "review_count": _safe_count(
                cursor,
                """
                SELECT COUNT(*)
                FROM recipes
                WHERE status = 'REVIEW'
                AND COALESCE(is_test_only, 0) = 0
                """
            ),
            "blocked_operation_count": _safe_count(
                cursor,
                """
                SELECT COUNT(*)
                FROM plc_operation_jobs
                WHERE status IN ('BLOCKED', 'FAILED')
                """
            ),
            "incomplete_recipe_count": _safe_count(
                cursor,
                """
                SELECT COUNT(*)
                FROM recipes r
                WHERE COALESCE(r.is_test_only, 0) = 0
                AND (
                    NOT EXISTS (
                        SELECT 1
                        FROM recipe_parameter_values v
                        WHERE v.recipe_id = r.id
                    )
                    OR NOT EXISTS (
                        SELECT 1
                        FROM recipe_phase_control pc
                        WHERE pc.recipe_id = r.id
                    )
                )
                """
            ),
            "plc_tag_typo_count": _safe_count(
                cursor,
                """
                SELECT COUNT(*)
                FROM plc_tags
                WHERE UPPER(tag_name) = 'CSR_DOWNLOAD_COMPLETE'
                """
            ),
            "test_only_recipe_count": _safe_count(
                cursor,
                """
                SELECT COUNT(*)
                FROM recipes
                WHERE COALESCE(is_test_only, 0) = 1
                """
            )
        }

        dashboard_alerts = _build_dashboard_alerts(
            session.get("role"),
            dashboard_counts
        )
        recipe_lifecycle = _build_recipe_lifecycle(cursor)
        stage_readiness = _build_stage_readiness(cursor)
        recent_activity = _build_recent_activity(cursor)

        conn.close()

        return render_template(
            "dashboard/dashboard.html",
            family_count=family_count,
            recipe_count=recipe_count,
            plc_count=plc_count,
            configured_plc_count=configured_plc_count,
            machine_count=machine_count,
            stage_count=stage_count,
            user_count=user_count,
            current_released_count=dashboard_counts["current_released_count"],
            dashboard_alerts=dashboard_alerts,
            recipe_lifecycle=recipe_lifecycle,
            stage_readiness=stage_readiness,
            recent_activity=recent_activity
        )
