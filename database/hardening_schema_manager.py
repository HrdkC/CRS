"""CRS V11.11 hardening migration.

This module is intentionally idempotent. It is executed only by bootstrap or an
explicit migration command, never by normal read-only request paths.
"""

import threading

from database.database import transaction


HARDENING_SCHEMA_VERSION = "CRS_V11_11_HARDENING_001"
RECIPE_RETENTION_SCHEMA_VERSION = "CRS_V13_RECIPE_RETENTION_001"

_SCHEMA_READY_LOCK = threading.Lock()
_SCHEMA_READY_VERIFIED = False


def _table_exists(cursor, table_name):
    return cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone() is not None


def _columns(cursor, table_name):
    if not _table_exists(cursor, table_name):
        return set()
    return {row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})")}


def _add_column(cursor, table_name, column_name, definition):
    if column_name not in _columns(cursor, table_name):
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def apply_v11_11_hardening_schema():
    with transaction(immediate=True) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                description TEXT,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Lock history is created here as a recovery-safe fallback. Normal new
        # installations also create it through the ordered bootstrap.
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
                heartbeat_at DATETIME,
                expires_at DATETIME,
                released_at DATETIME,
                release_reason TEXT,
                notes TEXT,
                lock_token TEXT,
                lease_version INTEGER DEFAULT 1,
                fencing_token INTEGER
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recipe_resource_locks_history
            ON recipe_resource_locks(resource_type, resource_id, created_at)
            """
        )

        # Atomic current-resource claims. recipe_resource_locks remains the
        # immutable history/audit table.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_resource_claims
            (
                resource_type TEXT NOT NULL,
                resource_id INTEGER NOT NULL,
                lock_id INTEGER NOT NULL,
                lock_token TEXT NOT NULL,
                fencing_token INTEGER NOT NULL,
                session_id INTEGER,
                locked_by TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                heartbeat_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                PRIMARY KEY(resource_type, resource_id),
                UNIQUE(lock_token)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recipe_resource_claims_expiry
            ON recipe_resource_claims(expires_at)
            """
        )

        if _table_exists(cursor, "recipe_resource_locks"):
            _add_column(cursor, "recipe_resource_locks", "lock_token", "TEXT")
            _add_column(cursor, "recipe_resource_locks", "lease_version", "INTEGER DEFAULT 1")
            _add_column(cursor, "recipe_resource_locks", "fencing_token", "INTEGER")
            _add_column(cursor, "recipe_resource_locks", "heartbeat_at", "DATETIME")

        if _table_exists(cursor, "audit_log"):
            _add_column(cursor, "audit_log", "correlation_id", "TEXT")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_log_correlation ON audit_log(correlation_id)"
            )

        if _table_exists(cursor, "recipe_parameter_audit"):
            _add_column(cursor, "recipe_parameter_audit", "correlation_id", "TEXT")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_recipe_parameter_audit_correlation "
                "ON recipe_parameter_audit(correlation_id)"
            )

        if _table_exists(cursor, "recipe_phase_control"):
            _add_column(cursor, "recipe_phase_control", "row_version", "INTEGER DEFAULT 0")

        if _table_exists(cursor, "recipe_status_history"):
            _add_column(cursor, "recipe_status_history", "remarks", "TEXT")
            _add_column(cursor, "recipe_status_history", "correlation_id", "TEXT")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_recipe_status_history_correlation "
                "ON recipe_status_history(correlation_id)"
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_phase_control_audit
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                correlation_id TEXT NOT NULL,
                recipe_id INTEGER NOT NULL,
                phase_row_id INTEGER NOT NULL,
                phase_group_code TEXT,
                line_no INTEGER,
                old_phase_control_id INTEGER,
                new_phase_control_id INTEGER,
                old_phase_name TEXT,
                new_phase_name TEXT,
                old_stop_option TEXT,
                new_stop_option TEXT,
                old_position_option TEXT,
                new_position_option TEXT,
                changed_by TEXT NOT NULL,
                user_role TEXT,
                change_source TEXT,
                change_reason TEXT NOT NULL,
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_phase_audit_recipe "
            "ON recipe_phase_control_audit(recipe_id, changed_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_phase_audit_correlation "
            "ON recipe_phase_control_audit(correlation_id)"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plc_operation_jobs
            (
                id TEXT PRIMARY KEY,
                recipe_id INTEGER,
                plc_id INTEGER,
                operation TEXT,
                title TEXT,
                status TEXT,
                success INTEGER,
                progress_percent INTEGER,
                current_step TEXT,
                started_by TEXT,
                user_role TEXT,
                result_json TEXT,
                correlation_id TEXT,
                worker_id TEXT,
                heartbeat_at DATETIME,
                recipe_lock_id INTEGER,
                plc_lock_id INTEGER,
                recovery_note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
            """
        )
        if _table_exists(cursor, "plc_operation_jobs"):
            _add_column(cursor, "plc_operation_jobs", "correlation_id", "TEXT")
            _add_column(cursor, "plc_operation_jobs", "worker_id", "TEXT")
            _add_column(cursor, "plc_operation_jobs", "heartbeat_at", "DATETIME")
            _add_column(cursor, "plc_operation_jobs", "recipe_lock_id", "INTEGER")
            _add_column(cursor, "plc_operation_jobs", "plc_lock_id", "INTEGER")
            _add_column(cursor, "plc_operation_jobs", "recovery_note", "TEXT")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_plc_jobs_queue "
            "ON plc_operation_jobs(status, created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_plc_jobs_plc_active "
            "ON plc_operation_jobs(plc_id, status, heartbeat_at)"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_settings
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_by TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stage_plc_tag_requirements
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                stage_id INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                label TEXT NOT NULL,
                requirement_level TEXT NOT NULL DEFAULT 'REQUIRED',
                expected_type TEXT,
                array_required INTEGER NOT NULL DEFAULT 0,
                minimum_array_size INTEGER,
                array_start_index INTEGER,
                array_end_index INTEGER,
                default_tag_name TEXT,
                search_hint TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                display_order INTEGER NOT NULL DEFAULT 100,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(machine_id, stage_id, purpose)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_upload_history
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plc_name TEXT, recipe_code TEXT, recipe_version INTEGER,
                uploaded_by TEXT, uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT, remarks TEXT, user_role TEXT, plc_id INTEGER,
                source_tag TEXT, destination_tag TEXT,
                candidate_change_count INTEGER DEFAULT 0,
                validated_parameters INTEGER DEFAULT 0,
                payload_mismatch_count INTEGER DEFAULT 0
            )
            """
        )
        for column_name, definition in {
            "user_role": "TEXT", "plc_id": "INTEGER", "source_tag": "TEXT",
            "destination_tag": "TEXT",
            "candidate_change_count": "INTEGER DEFAULT 0",
            "validated_parameters": "INTEGER DEFAULT 0",
            "payload_mismatch_count": "INTEGER DEFAULT 0",
        }.items():
            _add_column(cursor, "recipe_upload_history", column_name, definition)

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_parameter_audit
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                recipe_parameter_value_id INTEGER NOT NULL,
                parameter_definition_id INTEGER NOT NULL,
                old_value REAL, new_value REAL, changed_by TEXT,
                recipe_code TEXT, recipe_version INTEGER, parameter_name TEXT,
                tag_index INTEGER, change_source TEXT DEFAULT 'DATABASE',
                change_reason TEXT, user_role TEXT, client_ip TEXT,
                workstation_name TEXT, correlation_id TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _add_column(cursor, "recipe_parameter_audit", "correlation_id", "TEXT")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipe_parameter_audit_correlation "
            "ON recipe_parameter_audit(correlation_id)"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log_archive
            (
                archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_audit_id INTEGER, username TEXT, role TEXT,
                workstation_name TEXT, client_ip TEXT, plc_name TEXT,
                recipe_code TEXT, recipe_version INTEGER, record_id TEXT,
                parameter_name TEXT, old_value TEXT, new_value TEXT,
                action TEXT, change_source TEXT, reason TEXT, user_agent TEXT,
                request_host TEXT, forwarded_for TEXT, timestamp DATETIME,
                archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                archived_by TEXT, archive_batch_id TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_archive_exports
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT, export_type TEXT,
                export_path TEXT, file_name TEXT, row_count INTEGER DEFAULT 0,
                exported_by TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                remarks TEXT
            )
            """
        )

        # V13 safe recipe retention. Active recipe data is archived first and
        # remains recoverable. Permanent deletion is restricted to unused
        # TEST-ONLY drafts and leaves a durable tombstone/audit record.
        if _table_exists(cursor, "recipes"):
            _add_column(cursor, "recipes", "is_archived", "INTEGER NOT NULL DEFAULT 0")
            _add_column(cursor, "recipes", "archived_at", "DATETIME")
            _add_column(cursor, "recipes", "archived_by", "TEXT")
            _add_column(cursor, "recipes", "archive_reason", "TEXT")
            _add_column(cursor, "recipes", "archived_previous_status", "TEXT")
            _add_column(cursor, "recipes", "archive_correlation_id", "TEXT")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_recipes_active_stage "
                "ON recipes(machine_id, stage_id, is_archived, recipe_code, version)"
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_retention_history
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER,
                recipe_code TEXT NOT NULL,
                recipe_name TEXT,
                recipe_version INTEGER,
                machine_id INTEGER,
                stage_id INTEGER,
                event_type TEXT NOT NULL,
                previous_status TEXT,
                actor TEXT NOT NULL,
                actor_role TEXT,
                reason TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                metadata_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipe_retention_history_recipe "
            "ON recipe_retention_history(recipe_id, created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipe_retention_history_code "
            "ON recipe_retention_history(recipe_code, recipe_version, created_at)"
        )

        # Final P15 Second Stage contract: recipe rows carry only group, line
        # and selected phase. Legacy columns are retained but cleared and no
        # longer participate in recipe behavior.
        if (
            _table_exists(cursor, "recipe_phase_control")
            and _table_exists(cursor, "recipes")
            and _table_exists(cursor, "machine_stages")
        ):
            phase_row_columns = _columns(cursor, "recipe_phase_control")
            set_parts = []
            if "stop_option" in phase_row_columns:
                set_parts.append("stop_option=NULL")
            if "position_option" in phase_row_columns:
                set_parts.append("position_option=NULL")
            if "position_flag" in phase_row_columns:
                set_parts.append("position_flag=NULL")
            if set_parts:
                cursor.execute(
                    f"""
                    UPDATE recipe_phase_control
                    SET {', '.join(set_parts)}
                    WHERE recipe_id IN (
                        SELECT r.id
                        FROM recipes r
                        JOIN machine_stages s ON s.id=r.stage_id
                        WHERE UPPER(REPLACE(COALESCE(s.stage_type, ''), ' ', '_'))
                              IN ('SECOND_STAGE', 'SECONDSTAGE', 'SS')
                    )
                    """
                )
            if {"phase_group_code", "used"}.issubset(phase_row_columns):
                cursor.execute(
                    """
                    UPDATE recipe_phase_control
                    SET used=0
                    WHERE recipe_id IN (
                        SELECT r.id
                        FROM recipes r
                        JOIN machine_stages s ON s.id=r.stage_id
                        WHERE UPPER(REPLACE(COALESCE(s.stage_type, ''), ' ', '_'))
                              IN ('SECOND_STAGE', 'SECONDSTAGE', 'SS')
                    )
                      AND UPPER(COALESCE(phase_group_code, ''))
                          NOT IN ('CAP_STRIP_SIDE', 'BT_SIDE')
                    """
                )

        if (
            _table_exists(cursor, "stage_plc_tag_requirements")
            and _table_exists(cursor, "machine_stages")
        ):
            cursor.execute(
                """
                UPDATE stage_plc_tag_requirements
                SET active=0, updated_at=CURRENT_TIMESTAMP
                WHERE stage_id IN (
                    SELECT id FROM machine_stages
                    WHERE UPPER(REPLACE(COALESCE(stage_type, ''), ' ', '_'))
                          IN ('SECOND_STAGE', 'SECONDSTAGE', 'SS')
                )
                  AND UPPER(purpose) IN (
                    'PHASE_STOP_STRING', 'PHASE_POSITION_STRING',
                    'CAP_STRIP_PHASE_STOP_STRING',
                    'CAP_STRIP_PHASE_POSITION_STRING',
                    'BT_PHASE_STOP_STRING', 'BT_PHASE_POSITION_STRING',
                    'SHAPING_PHASE_CONTROL_STRING',
                    'SHAPING_PHASE_STOP_STRING',
                    'SHAPING_PHASE_POSITION_STRING'
                  )
                """
            )

        if _table_exists(cursor, "phase_control_master"):
            _add_column(cursor, "phase_control_master", "phase_control_key", "TEXT")
            _add_column(cursor, "phase_control_master", "plc_phase_code", "INTEGER")
            cursor.execute(
                """
                UPDATE phase_control_master
                SET phase_control_key=UPPER(TRIM(COALESCE(phase_control_name, '')))
                WHERE phase_control_key IS NULL OR TRIM(phase_control_key)=''
                """
            )

        # Shared, restart-safe login throttling.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS login_throttle
            (
                username_key TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                failure_count INTEGER NOT NULL DEFAULT 0,
                first_failure_at DATETIME,
                last_failure_at DATETIME,
                blocked_until DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(username_key, client_ip)
            )
            """
        )

        # Resolve pre-existing duplicate active sessions before enforcing one
        # case-insensitive active username.
        if _table_exists(cursor, "user_sessions"):
            duplicates = cursor.execute(
                """
                SELECT LOWER(username) AS username_key, MAX(id) AS keep_id
                FROM user_sessions
                WHERE logout_time IS NULL
                GROUP BY LOWER(username)
                HAVING COUNT(*) > 1
                """
            ).fetchall()
            for row in duplicates:
                cursor.execute(
                    """
                    UPDATE user_sessions
                    SET logout_time = CURRENT_TIMESTAMP,
                        logout_reason = 'DUPLICATE_ACTIVE_SESSION_CLOSED_BY_V11_11_MIGRATION'
                    WHERE LOWER(username) = ?
                      AND logout_time IS NULL
                      AND id <> ?
                    """,
                    (row[0], row[1]),
                )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_user_sessions_one_active_username
                ON user_sessions(LOWER(username))
                WHERE logout_time IS NULL
                """
            )

        if _table_exists(cursor, "users"):
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_nocase
                ON users(LOWER(username))
                """
            )

        cursor.execute(
            """
            INSERT OR IGNORE INTO schema_version(version, description)
            VALUES (?, ?)
            """,
            (
                HARDENING_SCHEMA_VERSION,
                "Atomic locks/sessions, audit correlation, durable PLC jobs and shared throttle",
            ),
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO schema_version(version, description)
            VALUES (?, ?)
            """,
            (
                RECIPE_RETENTION_SCHEMA_VERSION,
                "Safe recipe archive, restore and restricted permanent-delete evidence",
            ),
        )

    return HARDENING_SCHEMA_VERSION


def assert_v11_11_hardening_schema_ready():
    """Verify the controlled migration once per process without executing DDL.

    The schema cannot legitimately change underneath a running CRS process.
    Caching this successful preflight avoids opening a second SQLite connection
    for every one-second browser status poll while the PLC worker is writing
    job progress.
    """
    global _SCHEMA_READY_VERIFIED

    if _SCHEMA_READY_VERIFIED:
        return True

    with _SCHEMA_READY_LOCK:
        if _SCHEMA_READY_VERIFIED:
            return True

        from database.database import get_connection

        required_tables = {
            "schema_version",
            "recipe_resource_locks",
            "recipe_resource_claims",
            "login_throttle",
            "recipe_phase_control_audit",
            "plc_operation_jobs",
        }
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            existing = {row[0] for row in rows}
            missing = sorted(required_tables - existing)
            if missing:
                raise RuntimeError(
                    "CRS hardening schema is not ready; missing tables: "
                    + ", ".join(missing)
                    + ". Run the controlled bootstrap/migration before starting CRS."
                )
            version = conn.execute(
                "SELECT 1 FROM schema_version WHERE version=?",
                (HARDENING_SCHEMA_VERSION,),
            ).fetchone()
            if not version:
                raise RuntimeError(
                    f"Required schema version {HARDENING_SCHEMA_VERSION} is not applied."
                )
        finally:
            conn.close()

        _SCHEMA_READY_VERIFIED = True
        return True


if __name__ == "__main__":
    print(apply_v11_11_hardening_schema())
