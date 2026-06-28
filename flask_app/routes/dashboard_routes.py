from flask import (
    redirect,
    render_template,
    session
)

from database.database import (
    get_connection
)

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
            dashboard_alerts=dashboard_alerts
        )
