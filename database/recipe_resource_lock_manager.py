from database.database import get_connection


class RecipeResourceLockManager:
    """Short-lived industrial resource locks for CRS recipe/PLC workflows.

    Purpose:
    - Prevent two users from editing the same recipe at the same time.
    - Prevent recipe edit while PLC buffer operation is running.
    - Prevent another PLC/buffer operation for the same recipe/PLC until the
      first job reaches a final status or the stale lock expires.

    Locks are intentionally DB-backed so they work across browser tabs and
    across different CRS users on the plant LAN.
    """

    ACTIVE_STATUS = "ACTIVE"
    FINAL_STATUSES = {"RELEASED", "EXPIRED", "CANCELLED"}

    @staticmethod
    def ensure_table():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_resource_locks
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_type TEXT NOT NULL,
                resource_id INTEGER NOT NULL,
                operation_type TEXT NOT NULL,
                locked_by TEXT NOT NULL,
                user_role TEXT,
                session_id INTEGER,
                workstation_name TEXT,
                client_ip TEXT,
                user_agent TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                released_at DATETIME,
                release_reason TEXT,
                notes TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recipe_resource_locks_active
            ON recipe_resource_locks(resource_type, resource_id, status, expires_at)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recipe_resource_locks_session
            ON recipe_resource_locks(session_id, status)
            """
        )
        conn.commit()
        conn.close()

    @staticmethod
    def cleanup_expired_locks():
        RecipeResourceLockManager.ensure_table()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE recipe_resource_locks
            SET status = 'EXPIRED',
                released_at = CURRENT_TIMESTAMP,
                release_reason = 'LOCK_EXPIRED_AUTOMATICALLY'
            WHERE status = 'ACTIVE'
              AND expires_at IS NOT NULL
              AND datetime(expires_at) <= datetime('now')
            """
        )
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    @staticmethod
    def get_active_lock(resource_type, resource_id):
        RecipeResourceLockManager.ensure_table()
        RecipeResourceLockManager.cleanup_expired_locks()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM recipe_resource_locks
            WHERE resource_type = ?
              AND resource_id = ?
              AND status = 'ACTIVE'
              AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (resource_type, int(resource_id))
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def active_lock_belongs_to(lock_row, username=None, session_id=None):
        if not lock_row:
            return False
        try:
            same_session = session_id and int(lock_row.get("session_id") or 0) == int(session_id)
        except Exception:
            same_session = False
        same_user = username and (lock_row.get("locked_by") or "").lower() == username.lower()
        return bool(same_session or same_user)

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
        """Acquire a lock or return the conflicting active lock.

        Returns:
            {"acquired": bool, "lock": dict|None, "active_lock": dict|None}
        """
        RecipeResourceLockManager.ensure_table()
        RecipeResourceLockManager.cleanup_expired_locks()

        active_lock = RecipeResourceLockManager.get_active_lock(resource_type, resource_id)
        if active_lock:
            if allow_same_session and RecipeResourceLockManager.active_lock_belongs_to(
                active_lock,
                username=username,
                session_id=session_id,
            ):
                RecipeResourceLockManager.extend_lock(active_lock["id"], ttl_minutes=ttl_minutes)
                active_lock = RecipeResourceLockManager.get_lock(active_lock["id"])
                return {"acquired": True, "lock": active_lock, "active_lock": active_lock}
            return {"acquired": False, "lock": None, "active_lock": active_lock}

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO recipe_resource_locks
            (
                resource_type,
                resource_id,
                operation_type,
                locked_by,
                user_role,
                session_id,
                workstation_name,
                client_ip,
                user_agent,
                status,
                expires_at,
                notes
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', datetime('now', ?), ?)
            """,
            (
                resource_type,
                int(resource_id),
                operation_type,
                username,
                user_role,
                session_id,
                workstation_name,
                client_ip,
                user_agent,
                f"+{int(ttl_minutes)} minutes",
                notes,
            )
        )
        lock_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"acquired": True, "lock": RecipeResourceLockManager.get_lock(lock_id), "active_lock": None}

    @staticmethod
    def extend_lock(lock_id, ttl_minutes=15):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE recipe_resource_locks
            SET expires_at = datetime('now', ?)
            WHERE id = ?
              AND status = 'ACTIVE'
            """,
            (f"+{int(ttl_minutes)} minutes", int(lock_id))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def release_lock(lock_id, reason="RELEASED"):
        if not lock_id:
            return False
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE recipe_resource_locks
            SET status = 'RELEASED',
                released_at = CURRENT_TIMESTAMP,
                release_reason = ?
            WHERE id = ?
              AND status = 'ACTIVE'
            """,
            (reason, int(lock_id))
        )
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    @staticmethod
    def release_resource(resource_type, resource_id, reason="RELEASED"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE recipe_resource_locks
            SET status = 'RELEASED',
                released_at = CURRENT_TIMESTAMP,
                release_reason = ?
            WHERE resource_type = ?
              AND resource_id = ?
              AND status = 'ACTIVE'
            """,
            (reason, resource_type, int(resource_id))
        )
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        return updated

    @staticmethod
    def release_session_locks(session_id, reason="SESSION_CLOSED"):
        if not session_id:
            return 0
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE recipe_resource_locks
            SET status = 'RELEASED',
                released_at = CURRENT_TIMESTAMP,
                release_reason = ?
            WHERE session_id = ?
              AND status = 'ACTIVE'
            """,
            (reason, int(session_id))
        )
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    @staticmethod
    def get_lock(lock_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM recipe_resource_locks
            WHERE id = ?
            """,
            (int(lock_id),)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_active_locks(limit=100):
        RecipeResourceLockManager.ensure_table()
        RecipeResourceLockManager.cleanup_expired_locks()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM recipe_resource_locks
            WHERE status = 'ACTIVE'
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (int(limit or 100),)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
