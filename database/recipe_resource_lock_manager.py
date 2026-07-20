import uuid

from database.database import get_connection, transaction
from database.hardening_schema_manager import assert_v11_11_hardening_schema_ready


class RecipeResourceLockManager:
    """Atomic DB-backed leases for recipe and PLC resources.

    `recipe_resource_claims` is the unique current-owner table. The existing
    `recipe_resource_locks` table remains immutable history with release state.
    """

    ACTIVE_STATUS = "ACTIVE"
    FINAL_STATUSES = {"RELEASED", "EXPIRED", "CANCELLED"}

    @staticmethod
    def ensure_table():
        # Bootstrap owns normal schema creation. This idempotent fallback keeps
        # upgraded installations safe when the migration has not yet been run.
        assert_v11_11_hardening_schema_ready()

    @staticmethod
    def _expire_claims(cursor):
        expired = cursor.execute(
            """
            SELECT lock_id
            FROM recipe_resource_claims
            WHERE datetime(expires_at) <= datetime('now')
            """
        ).fetchall()
        lock_ids = [int(row[0]) for row in expired]
        if lock_ids:
            placeholders = ",".join("?" for _ in lock_ids)
            cursor.execute(
                f"""
                UPDATE recipe_resource_locks
                SET status='EXPIRED',
                    released_at=CURRENT_TIMESTAMP,
                    release_reason='LOCK_EXPIRED_AUTOMATICALLY'
                WHERE id IN ({placeholders}) AND status='ACTIVE'
                """,
                lock_ids,
            )
            cursor.execute(
                f"DELETE FROM recipe_resource_claims WHERE lock_id IN ({placeholders})",
                lock_ids,
            )
        return len(lock_ids)

    @staticmethod
    def cleanup_expired_locks():
        RecipeResourceLockManager.ensure_table()
        with transaction(immediate=True) as conn:
            return RecipeResourceLockManager._expire_claims(conn.cursor())

    @staticmethod
    def _claim_to_dict(row):
        return dict(row) if row else None

    @staticmethod
    def get_active_lock(resource_type, resource_id):
        RecipeResourceLockManager.ensure_table()
        RecipeResourceLockManager.cleanup_expired_locks()
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT h.*, c.lock_token, c.fencing_token,
                       c.heartbeat_at AS claim_heartbeat_at,
                       c.expires_at AS claim_expires_at
                FROM recipe_resource_claims c
                JOIN recipe_resource_locks h ON h.id = c.lock_id
                WHERE c.resource_type=? AND c.resource_id=?
                LIMIT 1
                """,
                (resource_type, int(resource_id)),
            ).fetchone()
            return RecipeResourceLockManager._claim_to_dict(row)
        finally:
            conn.close()

    @staticmethod
    def active_lock_belongs_to(lock_row, username=None, session_id=None):
        if not lock_row or not session_id:
            return False
        try:
            return int(lock_row.get("session_id") or 0) == int(session_id)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def acquire_lock(
        resource_type,
        resource_id,
        operation_type,
        username,
        user_role=None,
        session_id=None,
        workstation_name=None,
        client_ip=None,
        user_agent=None,
        ttl_minutes=15,
        notes=None,
        allow_same_session=True,
    ):
        RecipeResourceLockManager.ensure_table()
        resource_id = int(resource_id)
        ttl_modifier = f"+{max(1, int(ttl_minutes))} minutes"

        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            RecipeResourceLockManager._expire_claims(cursor)
            existing = cursor.execute(
                """
                SELECT h.*, c.lock_token, c.fencing_token,
                       c.heartbeat_at AS claim_heartbeat_at,
                       c.expires_at AS claim_expires_at
                FROM recipe_resource_claims c
                JOIN recipe_resource_locks h ON h.id=c.lock_id
                WHERE c.resource_type=? AND c.resource_id=?
                """,
                (resource_type, resource_id),
            ).fetchone()

            if existing:
                existing_dict = dict(existing)
                if (
                    allow_same_session
                    and session_id
                    and RecipeResourceLockManager.active_lock_belongs_to(
                        existing_dict, session_id=session_id
                    )
                ):
                    cursor.execute(
                        """
                        UPDATE recipe_resource_claims
                        SET heartbeat_at=CURRENT_TIMESTAMP,
                            expires_at=datetime('now', ?)
                        WHERE resource_type=? AND resource_id=? AND session_id=?
                        """,
                        (ttl_modifier, resource_type, resource_id, int(session_id)),
                    )
                    cursor.execute(
                        """
                        UPDATE recipe_resource_locks
                        SET heartbeat_at=CURRENT_TIMESTAMP,
                            expires_at=datetime('now', ?),
                            lease_version=COALESCE(lease_version, 0)+1
                        WHERE id=? AND status='ACTIVE'
                        """,
                        (ttl_modifier, existing_dict["id"]),
                    )
                    refreshed = cursor.execute(
                        "SELECT * FROM recipe_resource_locks WHERE id=?",
                        (existing_dict["id"],),
                    ).fetchone()
                    return {
                        "acquired": True,
                        "lock": dict(refreshed),
                        "active_lock": dict(refreshed),
                    }
                return {
                    "acquired": False,
                    "lock": None,
                    "active_lock": existing_dict,
                }

            fencing_token = int(
                cursor.execute(
                    """
                    SELECT COALESCE(MAX(fencing_token), 0)+1
                    FROM recipe_resource_locks
                    WHERE resource_type=? AND resource_id=?
                    """,
                    (resource_type, resource_id),
                ).fetchone()[0]
            )
            lock_token = uuid.uuid4().hex
            cursor.execute(
                """
                INSERT INTO recipe_resource_locks
                (
                    resource_type, resource_id, operation_type, locked_by,
                    user_role, session_id, workstation_name, client_ip,
                    user_agent, status, created_at, heartbeat_at, expires_at,
                    notes, lock_token, lease_version, fencing_token
                )
                VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP,
                 CURRENT_TIMESTAMP, datetime('now', ?), ?, ?, 1, ?)
                """,
                (
                    resource_type,
                    resource_id,
                    operation_type,
                    username,
                    user_role,
                    session_id,
                    workstation_name,
                    client_ip,
                    user_agent,
                    ttl_modifier,
                    notes,
                    lock_token,
                    fencing_token,
                ),
            )
            lock_id = int(cursor.lastrowid)
            cursor.execute(
                """
                INSERT INTO recipe_resource_claims
                (
                    resource_type, resource_id, lock_id, lock_token,
                    fencing_token, session_id, locked_by, operation_type,
                    heartbeat_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, datetime('now', ?))
                """,
                (
                    resource_type,
                    resource_id,
                    lock_id,
                    lock_token,
                    fencing_token,
                    session_id,
                    username,
                    operation_type,
                    ttl_modifier,
                ),
            )
            lock = cursor.execute(
                "SELECT * FROM recipe_resource_locks WHERE id=?", (lock_id,)
            ).fetchone()
            return {"acquired": True, "lock": dict(lock), "active_lock": None}

    @staticmethod
    def extend_lock(lock_id, ttl_minutes=15, lock_token=None, session_id=None):
        RecipeResourceLockManager.ensure_table()
        ttl_modifier = f"+{max(1, int(ttl_minutes))} minutes"
        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            claim = cursor.execute(
                "SELECT * FROM recipe_resource_claims WHERE lock_id=?",
                (int(lock_id),),
            ).fetchone()
            if not claim:
                return False
            if lock_token and claim["lock_token"] != lock_token:
                return False
            if session_id and int(claim["session_id"] or 0) != int(session_id):
                return False
            cursor.execute(
                """
                UPDATE recipe_resource_claims
                SET heartbeat_at=CURRENT_TIMESTAMP,
                    expires_at=datetime('now', ?)
                WHERE lock_id=?
                """,
                (ttl_modifier, int(lock_id)),
            )
            cursor.execute(
                """
                UPDATE recipe_resource_locks
                SET heartbeat_at=CURRENT_TIMESTAMP,
                    expires_at=datetime('now', ?),
                    lease_version=COALESCE(lease_version, 0)+1
                WHERE id=? AND status='ACTIVE'
                """,
                (ttl_modifier, int(lock_id)),
            )
            return cursor.rowcount > 0

    @staticmethod
    def release_lock(lock_id, reason="RELEASED", lock_token=None, session_id=None):
        if not lock_id:
            return False
        RecipeResourceLockManager.ensure_table()
        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            claim = cursor.execute(
                "SELECT * FROM recipe_resource_claims WHERE lock_id=?",
                (int(lock_id),),
            ).fetchone()
            if claim:
                if lock_token and claim["lock_token"] != lock_token:
                    return False
                if session_id and int(claim["session_id"] or 0) != int(session_id):
                    return False
                cursor.execute(
                    "DELETE FROM recipe_resource_claims WHERE lock_id=?",
                    (int(lock_id),),
                )
            cursor.execute(
                """
                UPDATE recipe_resource_locks
                SET status='RELEASED', released_at=CURRENT_TIMESTAMP,
                    release_reason=?
                WHERE id=? AND status='ACTIVE'
                """,
                (reason, int(lock_id)),
            )
            return cursor.rowcount > 0

    @staticmethod
    def release_resource(resource_type, resource_id, reason="RELEASED"):
        RecipeResourceLockManager.ensure_table()
        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            lock_ids = [
                row[0]
                for row in cursor.execute(
                    "SELECT lock_id FROM recipe_resource_claims WHERE resource_type=? AND resource_id=?",
                    (resource_type, int(resource_id)),
                ).fetchall()
            ]
            cursor.execute(
                "DELETE FROM recipe_resource_claims WHERE resource_type=? AND resource_id=?",
                (resource_type, int(resource_id)),
            )
            if not lock_ids:
                return 0
            placeholders = ",".join("?" for _ in lock_ids)
            cursor.execute(
                f"""
                UPDATE recipe_resource_locks
                SET status='RELEASED', released_at=CURRENT_TIMESTAMP,
                    release_reason=?
                WHERE id IN ({placeholders}) AND status='ACTIVE'
                """,
                [reason] + lock_ids,
            )
            return cursor.rowcount

    @staticmethod
    def release_session_locks(session_id, reason="SESSION_CLOSED"):
        if not session_id:
            return 0
        RecipeResourceLockManager.ensure_table()
        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            lock_ids = [
                row[0]
                for row in cursor.execute(
                    "SELECT lock_id FROM recipe_resource_claims WHERE session_id=?",
                    (int(session_id),),
                ).fetchall()
            ]
            cursor.execute(
                "DELETE FROM recipe_resource_claims WHERE session_id=?",
                (int(session_id),),
            )
            if not lock_ids:
                return 0
            placeholders = ",".join("?" for _ in lock_ids)
            cursor.execute(
                f"""
                UPDATE recipe_resource_locks
                SET status='RELEASED', released_at=CURRENT_TIMESTAMP,
                    release_reason=?
                WHERE id IN ({placeholders}) AND status='ACTIVE'
                """,
                [reason] + lock_ids,
            )
            return cursor.rowcount

    @staticmethod
    def release_current_user_resource(
        resource_type,
        resource_id,
        username=None,
        session_id=None,
        reason="USER_RELEASED_LOCK",
    ):
        if not session_id:
            return 0
        RecipeResourceLockManager.ensure_table()
        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            claim = cursor.execute(
                """
                SELECT lock_id FROM recipe_resource_claims
                WHERE resource_type=? AND resource_id=? AND session_id=?
                """,
                (resource_type, int(resource_id), int(session_id)),
            ).fetchone()
            if not claim:
                return 0
            lock_id = int(claim[0])
            cursor.execute(
                "DELETE FROM recipe_resource_claims WHERE lock_id=?", (lock_id,)
            )
            cursor.execute(
                """
                UPDATE recipe_resource_locks
                SET status='RELEASED', released_at=CURRENT_TIMESTAMP,
                    release_reason=?
                WHERE id=? AND status='ACTIVE'
                """,
                (reason, lock_id),
            )
            return cursor.rowcount

    @staticmethod
    def get_current_user_active_lock(resource_type, resource_id, username=None, session_id=None):
        lock = RecipeResourceLockManager.get_active_lock(resource_type, resource_id)
        if RecipeResourceLockManager.active_lock_belongs_to(
            lock, username=username, session_id=session_id
        ):
            return lock
        return None

    @staticmethod
    def get_lock(lock_id):
        RecipeResourceLockManager.ensure_table()
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM recipe_resource_locks WHERE id=?", (int(lock_id),)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_active_locks(limit=100):
        RecipeResourceLockManager.ensure_table()
        RecipeResourceLockManager.cleanup_expired_locks()
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT h.*, c.lock_token, c.fencing_token,
                       c.heartbeat_at AS claim_heartbeat_at,
                       c.expires_at AS claim_expires_at
                FROM recipe_resource_claims c
                JOIN recipe_resource_locks h ON h.id=c.lock_id
                ORDER BY c.heartbeat_at DESC
                LIMIT ?
                """,
                (max(1, min(int(limit), 1000)),),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
