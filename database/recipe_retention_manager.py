"""Safe recipe archive, restore, and restricted permanent deletion.

The normal operator action is Archive. Permanent deletion is intentionally
limited to archived TEST-ONLY drafts that have never entered a controlled
lifecycle or PLC operation. Audit/tombstone evidence is retained.
"""

from __future__ import annotations

import json
import uuid

from database.audit_manager import AuditManager
from database.database import get_connection, transaction


class RecipeRetentionManager:
    ARCHIVEABLE_STATUSES = {"DRAFT", "REVIEW", "APPROVED"}
    ACTIVE_JOB_STATUSES = {"QUEUED", "RUNNING"}
    ADVANCED_STATUSES = {"REVIEW", "APPROVED", "RELEASED"}

    @staticmethod
    def _table_exists(conn, table_name):
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone() is not None

    @staticmethod
    def _columns(conn, table_name):
        if not RecipeRetentionManager._table_exists(conn, table_name):
            return set()
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}

    @staticmethod
    def schema_ready(conn=None):
        owns = conn is None
        conn = conn or get_connection()
        try:
            required_columns = {
                "is_archived",
                "archived_at",
                "archived_by",
                "archive_reason",
                "archived_previous_status",
                "archive_correlation_id",
            }
            return (
                required_columns.issubset(
                    RecipeRetentionManager._columns(conn, "recipes")
                )
                and RecipeRetentionManager._table_exists(
                    conn, "recipe_retention_history"
                )
            )
        finally:
            if owns:
                conn.close()

    @staticmethod
    def assert_schema_ready(conn=None):
        if not RecipeRetentionManager.schema_ready(conn):
            raise RuntimeError(
                "Recipe archive schema is not installed. Stop CRS and run "
                "python scripts\\bootstrap_crs_system.py --no-seed-users, then restart."
            )
        return True

    @staticmethod
    def _count(conn, sql, params=()):
        row = conn.execute(sql, params).fetchone()
        return int(row[0] if row else 0)

    @staticmethod
    def _recipe_row(conn, recipe_id):
        return conn.execute(
            """
            SELECT
                r.*,
                m.machine_code,
                s.stage_type,
                CASE
                    WHEN r.status='RELEASED'
                     AND r.version=(
                        SELECT MAX(x.version)
                        FROM recipes x
                        WHERE x.machine_id=r.machine_id
                          AND x.stage_id=r.stage_id
                          AND UPPER(x.recipe_code)=UPPER(r.recipe_code)
                          AND x.status='RELEASED'
                          AND COALESCE(x.is_archived, 0)=0
                     )
                    THEN 1 ELSE 0
                END AS is_current_released
            FROM recipes r
            LEFT JOIN tbm_machines m ON m.id=r.machine_id
            LEFT JOIN machine_stages s ON s.id=r.stage_id
            WHERE r.id=?
            """,
            (int(recipe_id),),
        ).fetchone()

    @staticmethod
    def _policy_with_connection(conn, recipe_id):
        RecipeRetentionManager.assert_schema_ready(conn)
        row = RecipeRetentionManager._recipe_row(conn, recipe_id)
        if not row:
            return {
                "exists": False,
                "can_archive": False,
                "can_restore": False,
                "can_permanently_delete": False,
                "archive_blockers": ["Recipe not found."],
                "restore_blockers": ["Recipe not found."],
                "delete_blockers": ["Recipe not found."],
            }

        recipe = dict(row)
        status = str(recipe.get("status") or "").upper()
        archived = int(recipe.get("is_archived") or 0) == 1

        active_jobs = 0
        total_jobs = 0
        if RecipeRetentionManager._table_exists(conn, "plc_operation_jobs"):
            active_jobs = RecipeRetentionManager._count(
                conn,
                """
                SELECT COUNT(*) FROM plc_operation_jobs
                WHERE recipe_id=? AND UPPER(COALESCE(status,'')) IN ('QUEUED','RUNNING')
                """,
                (int(recipe_id),),
            )
            total_jobs = RecipeRetentionManager._count(
                conn,
                "SELECT COUNT(*) FROM plc_operation_jobs WHERE recipe_id=?",
                (int(recipe_id),),
            )

        active_claims = 0
        if RecipeRetentionManager._table_exists(conn, "recipe_resource_claims"):
            active_claims = RecipeRetentionManager._count(
                conn,
                """
                SELECT COUNT(*) FROM recipe_resource_claims
                WHERE resource_id=?
                  AND UPPER(resource_type) IN ('RECIPE_EDIT','RECIPE_OPERATION')
                  AND datetime(expires_at) > datetime('now')
                """,
                (int(recipe_id),),
            )

        advanced_history = 0
        if RecipeRetentionManager._table_exists(conn, "recipe_status_history"):
            advanced_history = RecipeRetentionManager._count(
                conn,
                """
                SELECT COUNT(*) FROM recipe_status_history
                WHERE recipe_id=?
                  AND UPPER(COALESCE(new_status,'')) IN ('REVIEW','APPROVED','RELEASED')
                """,
                (int(recipe_id),),
            )

        sibling_released = RecipeRetentionManager._count(
            conn,
            """
            SELECT COUNT(*) FROM recipes
            WHERE machine_id=? AND stage_id=?
              AND UPPER(recipe_code)=UPPER(?)
              AND status='RELEASED'
            """,
            (
                recipe.get("machine_id"),
                recipe.get("stage_id"),
                recipe.get("recipe_code"),
            ),
        )

        download_history = 0
        if RecipeRetentionManager._table_exists(conn, "recipe_download_history"):
            download_history = RecipeRetentionManager._count(
                conn,
                """
                SELECT COUNT(*) FROM recipe_download_history
                WHERE UPPER(COALESCE(recipe_code,''))=UPPER(?)
                  AND COALESCE(recipe_version, 1)=?
                """,
                (recipe.get("recipe_code"), int(recipe.get("version") or 1)),
            )

        upload_history = 0
        if RecipeRetentionManager._table_exists(conn, "recipe_upload_history"):
            upload_history = RecipeRetentionManager._count(
                conn,
                """
                SELECT COUNT(*) FROM recipe_upload_history
                WHERE UPPER(COALESCE(recipe_code,''))=UPPER(?)
                  AND COALESCE(recipe_version, 1)=?
                """,
                (recipe.get("recipe_code"), int(recipe.get("version") or 1)),
            )

        version_snapshots = 0
        if RecipeRetentionManager._table_exists(conn, "recipe_versions"):
            version_snapshots = RecipeRetentionManager._count(
                conn,
                """
                SELECT COUNT(*) FROM recipe_versions
                WHERE recipe_id=? OR (
                    UPPER(COALESCE(recipe_code,''))=UPPER(?)
                    AND COALESCE(version, 1)=?
                )
                """,
                (
                    int(recipe_id),
                    recipe.get("recipe_code"),
                    int(recipe.get("version") or 1),
                ),
            )

        archive_blockers = []
        if archived:
            archive_blockers.append("Recipe is already archived.")
        if status not in RecipeRetentionManager.ARCHIVEABLE_STATUSES:
            archive_blockers.append(
                "Only Draft, Review, or Approved recipes can be archived. "
                "Released production history is protected."
            )
        if int(recipe.get("is_current_released") or 0) == 1:
            archive_blockers.append("Current production recipe cannot be archived.")
        if active_jobs:
            archive_blockers.append("An active PLC/buffer operation is running.")
        if active_claims:
            archive_blockers.append("The recipe is currently locked for edit or operation.")

        restore_blockers = []
        if not archived:
            restore_blockers.append("Recipe is not archived.")
        if active_jobs:
            restore_blockers.append("An active PLC/buffer operation is running.")
        if active_claims:
            restore_blockers.append("The recipe is currently locked.")

        delete_blockers = []
        if not archived:
            delete_blockers.append("Archive the recipe before permanent deletion.")
        if status != "DRAFT":
            delete_blockers.append("Only archived Draft recipes can be permanently deleted.")
        if int(recipe.get("is_test_only") or 0) != 1:
            delete_blockers.append("Permanent deletion is restricted to TEST ONLY recipes.")
        if advanced_history:
            delete_blockers.append(
                "Recipe entered Review, Approved, or Released lifecycle and is protected."
            )
        if sibling_released:
            delete_blockers.append(
                "A released version exists under the same recipe code."
            )
        if total_jobs:
            delete_blockers.append("Recipe has PLC/buffer operation history.")
        if download_history or upload_history:
            delete_blockers.append("Recipe has PLC download/upload history.")
        if version_snapshots:
            delete_blockers.append("Recipe has retained version snapshots.")
        if active_jobs:
            delete_blockers.append("An active PLC/buffer operation is running.")
        if active_claims:
            delete_blockers.append("The recipe is currently locked.")

        return {
            "exists": True,
            "recipe": recipe,
            "can_archive": not archive_blockers,
            "can_restore": not restore_blockers,
            "can_permanently_delete": not delete_blockers,
            "archive_blockers": archive_blockers,
            "restore_blockers": restore_blockers,
            "delete_blockers": delete_blockers,
            "counts": {
                "active_jobs": active_jobs,
                "total_jobs": total_jobs,
                "active_claims": active_claims,
                "advanced_history": advanced_history,
                "sibling_released": sibling_released,
                "download_history": download_history,
                "upload_history": upload_history,
                "version_snapshots": version_snapshots,
            },
        }

    @staticmethod
    def get_policy(recipe_id):
        conn = get_connection()
        try:
            return RecipeRetentionManager._policy_with_connection(conn, recipe_id)
        finally:
            conn.close()

    @staticmethod
    def get_recipe_record(recipe_id):
        conn = get_connection()
        try:
            RecipeRetentionManager.assert_schema_ready(conn)
            row = RecipeRetentionManager._recipe_row(conn, recipe_id)
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def list_archived(machine_id, stage_id):
        conn = get_connection()
        try:
            RecipeRetentionManager.assert_schema_ready(conn)
            rows = conn.execute(
                """
                SELECT r.*, m.machine_code, s.stage_type
                FROM recipes r
                LEFT JOIN tbm_machines m ON m.id=r.machine_id
                LEFT JOIN machine_stages s ON s.id=r.stage_id
                WHERE r.machine_id=? AND r.stage_id=?
                  AND COALESCE(r.is_archived,0)=1
                ORDER BY datetime(r.archived_at) DESC, r.recipe_code, r.version DESC
                """,
                (int(machine_id), int(stage_id)),
            ).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                policy = RecipeRetentionManager._policy_with_connection(
                    conn, item["id"]
                )
                item.update(
                    can_restore=policy["can_restore"],
                    can_permanently_delete=policy["can_permanently_delete"],
                    restore_blockers=policy["restore_blockers"],
                    delete_blockers=policy["delete_blockers"],
                )
                result.append(item)
            return result
        finally:
            conn.close()

    @staticmethod
    def _validate_confirmation(recipe, confirmation_code, reason):
        reason = str(reason or "").strip()
        confirmation_code = str(confirmation_code or "").strip()
        if len(reason) < 5:
            raise ValueError("A clear reason of at least 5 characters is required.")
        if confirmation_code.upper() != str(recipe.get("recipe_code") or "").upper():
            raise ValueError("Confirmation recipe code does not match.")
        return reason

    @staticmethod
    def _insert_history(
        conn,
        recipe,
        event_type,
        actor,
        actor_role,
        reason,
        correlation_id,
        metadata=None,
    ):
        conn.execute(
            """
            INSERT INTO recipe_retention_history
            (recipe_id, recipe_code, recipe_name, recipe_version,
             machine_id, stage_id, event_type, previous_status,
             actor, actor_role, reason, correlation_id, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipe.get("id"),
                recipe.get("recipe_code"),
                recipe.get("recipe_name"),
                recipe.get("version"),
                recipe.get("machine_id"),
                recipe.get("stage_id"),
                event_type,
                recipe.get("status"),
                actor,
                actor_role,
                reason,
                correlation_id,
                json.dumps(metadata or {}, sort_keys=True, default=str),
            ),
        )

    @staticmethod
    def archive_recipe(
        recipe_id,
        actor,
        actor_role,
        reason,
        confirmation_code,
        request_context=None,
    ):
        correlation_id = uuid.uuid4().hex
        with transaction(immediate=True) as conn:
            policy = RecipeRetentionManager._policy_with_connection(conn, recipe_id)
            if not policy.get("exists"):
                raise ValueError("Recipe not found.")
            recipe = policy["recipe"]
            reason = RecipeRetentionManager._validate_confirmation(
                recipe, confirmation_code, reason
            )
            if not policy["can_archive"]:
                raise ValueError(" ".join(policy["archive_blockers"]))

            conn.execute(
                """
                UPDATE recipes
                SET is_archived=1,
                    archived_at=CURRENT_TIMESTAMP,
                    archived_by=?,
                    archive_reason=?,
                    archived_previous_status=status,
                    archive_correlation_id=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND COALESCE(is_archived,0)=0
                """,
                (actor, reason, correlation_id, int(recipe_id)),
            )
            RecipeRetentionManager._insert_history(
                conn, recipe, "ARCHIVED", actor, actor_role,
                reason, correlation_id, policy.get("counts")
            )
            ctx = request_context or {}
            AuditManager.log_event(
                username=actor,
                role=actor_role,
                action="RECIPE_ARCHIVED",
                change_source="RECIPE_RETENTION",
                recipe_code=recipe.get("recipe_code"),
                recipe_version=recipe.get("version"),
                record_id=recipe.get("id"),
                old_value=f"status={recipe.get('status')}; archived=0",
                new_value="archived=1",
                reason=reason,
                workstation_name=ctx.get("workstation_name"),
                client_ip=ctx.get("client_ip"),
                user_agent=ctx.get("user_agent"),
                forwarded_for=ctx.get("forwarded_for"),
                request_host=ctx.get("request_host"),
                correlation_id=correlation_id,
                _connection=conn,
            )
            return dict(recipe, correlation_id=correlation_id)

    @staticmethod
    def restore_recipe(
        recipe_id,
        actor,
        actor_role,
        reason,
        confirmation_code,
        request_context=None,
    ):
        correlation_id = uuid.uuid4().hex
        with transaction(immediate=True) as conn:
            policy = RecipeRetentionManager._policy_with_connection(conn, recipe_id)
            if not policy.get("exists"):
                raise ValueError("Recipe not found.")
            recipe = policy["recipe"]
            reason = RecipeRetentionManager._validate_confirmation(
                recipe, confirmation_code, reason
            )
            if not policy["can_restore"]:
                raise ValueError(" ".join(policy["restore_blockers"]))

            conn.execute(
                """
                UPDATE recipes
                SET is_archived=0,
                    archived_at=NULL,
                    archived_by=NULL,
                    archive_reason=NULL,
                    archived_previous_status=NULL,
                    archive_correlation_id=NULL,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND COALESCE(is_archived,0)=1
                """,
                (int(recipe_id),),
            )
            RecipeRetentionManager._insert_history(
                conn, recipe, "RESTORED", actor, actor_role,
                reason, correlation_id, policy.get("counts")
            )
            ctx = request_context or {}
            AuditManager.log_event(
                username=actor,
                role=actor_role,
                action="RECIPE_ARCHIVE_RESTORED",
                change_source="RECIPE_RETENTION",
                recipe_code=recipe.get("recipe_code"),
                recipe_version=recipe.get("version"),
                record_id=recipe.get("id"),
                old_value="archived=1",
                new_value=f"archived=0; status={recipe.get('status')}",
                reason=reason,
                workstation_name=ctx.get("workstation_name"),
                client_ip=ctx.get("client_ip"),
                user_agent=ctx.get("user_agent"),
                forwarded_for=ctx.get("forwarded_for"),
                request_host=ctx.get("request_host"),
                correlation_id=correlation_id,
                _connection=conn,
            )
            return dict(recipe, correlation_id=correlation_id)

    @staticmethod
    def permanently_delete_recipe(
        recipe_id,
        actor,
        actor_role,
        reason,
        confirmation_code,
        delete_confirmation=None,
        request_context=None,
    ):
        correlation_id = uuid.uuid4().hex
        with transaction(immediate=True) as conn:
            policy = RecipeRetentionManager._policy_with_connection(conn, recipe_id)
            if not policy.get("exists"):
                raise ValueError("Recipe not found.")
            recipe = policy["recipe"]
            reason = RecipeRetentionManager._validate_confirmation(
                recipe, confirmation_code, reason
            )
            # The operator already selected Delete Permanently from the archived
            # recipe list and is submitting an ADMIN-only CSRF-protected form.
            # `delete_confirmation` remains an ignored compatibility argument for
            # older callers; permanent deletion still requires an eligible archived
            # TEST ONLY draft and a mandatory reason.
            if not policy["can_permanently_delete"]:
                raise ValueError(" ".join(policy["delete_blockers"]))

            snapshot = dict(policy.get("counts") or {})
            for table, key in (
                ("recipe_parameter_values", "parameter_values"),
                ("recipe_phase_control", "phase_rows"),
                ("recipe_status_history", "status_history_rows"),
                ("recipe_parameter_audit", "parameter_audit_rows_retained"),
                ("recipe_phase_control_audit", "phase_audit_rows_retained"),
            ):
                if RecipeRetentionManager._table_exists(conn, table):
                    snapshot[key] = RecipeRetentionManager._count(
                        conn,
                        f"SELECT COUNT(*) FROM {table} WHERE recipe_id=?",
                        (int(recipe_id),),
                    )

            RecipeRetentionManager._insert_history(
                conn, recipe, "PERMANENTLY_DELETED", actor, actor_role,
                reason, correlation_id, snapshot
            )

            if RecipeRetentionManager._table_exists(conn, "recipe_version_values") and RecipeRetentionManager._table_exists(conn, "recipe_versions"):
                conn.execute(
                    """
                    DELETE FROM recipe_version_values
                    WHERE recipe_version_id IN (
                        SELECT id FROM recipe_versions
                        WHERE recipe_id=? OR (
                            UPPER(COALESCE(recipe_code,''))=UPPER(?)
                            AND COALESCE(version,1)=?
                        )
                    )
                    """,
                    (
                        int(recipe_id),
                        recipe.get("recipe_code"),
                        int(recipe.get("version") or 1),
                    ),
                )
            if RecipeRetentionManager._table_exists(conn, "recipe_versions"):
                conn.execute(
                    """
                    DELETE FROM recipe_versions
                    WHERE recipe_id=? OR (
                        UPPER(COALESCE(recipe_code,''))=UPPER(?)
                        AND COALESCE(version,1)=?
                    )
                    """,
                    (
                        int(recipe_id),
                        recipe.get("recipe_code"),
                        int(recipe.get("version") or 1),
                    ),
                )
            for table in (
                "recipe_parameter_values",
                "recipe_phase_control",
                "recipe_status_history",
            ):
                if RecipeRetentionManager._table_exists(conn, table):
                    conn.execute(
                        f"DELETE FROM {table} WHERE recipe_id=?",
                        (int(recipe_id),),
                    )

            deleted = conn.execute(
                "DELETE FROM recipes WHERE id=? AND COALESCE(is_archived,0)=1",
                (int(recipe_id),),
            )
            if deleted.rowcount != 1:
                raise RuntimeError("Recipe deletion did not complete; transaction rolled back.")

            ctx = request_context or {}
            AuditManager.log_event(
                username=actor,
                role=actor_role,
                action="RECIPE_PERMANENTLY_DELETED",
                change_source="RECIPE_RETENTION",
                recipe_code=recipe.get("recipe_code"),
                recipe_version=recipe.get("version"),
                record_id=recipe.get("id"),
                old_value=json.dumps(
                    {
                        "recipe_name": recipe.get("recipe_name"),
                        "status": recipe.get("status"),
                        "is_test_only": recipe.get("is_test_only"),
                        "deleted_counts": snapshot,
                    },
                    sort_keys=True,
                    default=str,
                ),
                new_value="PERMANENTLY_DELETED; tombstone retained",
                reason=reason,
                workstation_name=ctx.get("workstation_name"),
                client_ip=ctx.get("client_ip"),
                user_agent=ctx.get("user_agent"),
                forwarded_for=ctx.get("forwarded_for"),
                request_host=ctx.get("request_host"),
                correlation_id=correlation_id,
                _connection=conn,
            )
            return dict(recipe, correlation_id=correlation_id, deleted_counts=snapshot)
