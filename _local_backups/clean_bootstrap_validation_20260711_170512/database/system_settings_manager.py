from config.settings import SESSION_TIMEOUT_MINUTES
from database.database import get_connection


class SystemSettingsManager:
    """Centralized application settings stored in SQLite.

    Environment variables still provide startup defaults, but Admin users can
    adjust selected settings from the GUI. The database value is treated as the
    source of truth after it is created.
    """

    SESSION_TIMEOUT_KEY = "SESSION_TIMEOUT_MINUTES"
    HEARTBEAT_STALE_GRACE_KEY = "SESSION_HEARTBEAT_STALE_GRACE_SECONDS"

    MIN_SESSION_TIMEOUT_MINUTES = 1
    MAX_SESSION_TIMEOUT_MINUTES = 480

    MIN_HEARTBEAT_STALE_GRACE_SECONDS = 30
    MAX_HEARTBEAT_STALE_GRACE_SECONDS = 600
    DEFAULT_HEARTBEAT_STALE_GRACE_SECONDS = 75

    @staticmethod
    def ensure_table():
        conn = get_connection()
        cursor = conn.cursor()

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

        # Backward-compatible upgrades for older system_settings table.
        cursor.execute("PRAGMA table_info(system_settings)")
        columns = {row[1] for row in cursor.fetchall()}

        if "updated_by" not in columns:
            cursor.execute("ALTER TABLE system_settings ADD COLUMN updated_by TEXT")

        if "updated_at" not in columns:
            cursor.execute("ALTER TABLE system_settings ADD COLUMN updated_at TIMESTAMP")
            cursor.execute(
                """
                UPDATE system_settings
                SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
                WHERE updated_at IS NULL
                """
            )

        conn.commit()
        conn.close()

    @staticmethod
    def set_setting(setting_key, setting_value, description=None, updated_by=None):
        SystemSettingsManager.ensure_table()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO system_settings
            (
                setting_key,
                setting_value,
                description,
                updated_by,
                updated_at
            )
            VALUES
            (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                description = excluded.description,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                setting_key,
                str(setting_value),
                description,
                updated_by,
            )
        )

        conn.commit()
        conn.close()

    @staticmethod
    def get_setting(setting_key, default_value=None):
        SystemSettingsManager.ensure_table()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT setting_value
            FROM system_settings
            WHERE setting_key = ?
            """,
            (setting_key,)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return row["setting_value"]

        return default_value

    @staticmethod
    def get_setting_record(setting_key):
        SystemSettingsManager.ensure_table()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM system_settings
            WHERE setting_key = ?
            """,
            (setting_key,)
        )

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    @staticmethod
    def get_int(setting_key, default_value):
        value = SystemSettingsManager.get_setting(
            setting_key=setting_key,
            default_value=default_value
        )

        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default_value)

    @staticmethod
    def ensure_session_timeout_setting(default_minutes=None):
        SystemSettingsManager.ensure_table()

        existing = SystemSettingsManager.get_setting_record(
            SystemSettingsManager.SESSION_TIMEOUT_KEY
        )

        if existing:
            SystemSettingsManager.ensure_heartbeat_stale_grace_setting()
            return

        default_minutes = int(default_minutes or SESSION_TIMEOUT_MINUTES)
        default_minutes = SystemSettingsManager.validate_session_timeout_minutes(
            default_minutes
        )

        SystemSettingsManager.set_setting(
            setting_key=SystemSettingsManager.SESSION_TIMEOUT_KEY,
            setting_value=default_minutes,
            description="Idle auto logout timeout in minutes. Configurable by ADMIN super user from Active Sessions GUI.",
            updated_by="SYSTEM"
        )

        SystemSettingsManager.ensure_heartbeat_stale_grace_setting()

    @staticmethod
    def validate_session_timeout_minutes(timeout_minutes):
        try:
            timeout_minutes = int(timeout_minutes)
        except (TypeError, ValueError):
            raise ValueError("Auto logout timeout must be a number.")

        if timeout_minutes < SystemSettingsManager.MIN_SESSION_TIMEOUT_MINUTES:
            raise ValueError(
                f"Auto logout timeout must be at least {SystemSettingsManager.MIN_SESSION_TIMEOUT_MINUTES} minute."
            )

        if timeout_minutes > SystemSettingsManager.MAX_SESSION_TIMEOUT_MINUTES:
            raise ValueError(
                f"Auto logout timeout cannot exceed {SystemSettingsManager.MAX_SESSION_TIMEOUT_MINUTES} minutes."
            )

        return timeout_minutes

    @staticmethod
    def validate_heartbeat_stale_grace_seconds(grace_seconds):
        try:
            grace_seconds = int(grace_seconds)
        except (TypeError, ValueError):
            raise ValueError("Browser-close stale grace must be a number of seconds.")

        if grace_seconds < SystemSettingsManager.MIN_HEARTBEAT_STALE_GRACE_SECONDS:
            raise ValueError(
                f"Browser-close stale grace must be at least {SystemSettingsManager.MIN_HEARTBEAT_STALE_GRACE_SECONDS} seconds."
            )

        if grace_seconds > SystemSettingsManager.MAX_HEARTBEAT_STALE_GRACE_SECONDS:
            raise ValueError(
                f"Browser-close stale grace cannot exceed {SystemSettingsManager.MAX_HEARTBEAT_STALE_GRACE_SECONDS} seconds."
            )

        return grace_seconds

    @staticmethod
    def ensure_heartbeat_stale_grace_setting(default_seconds=None):
        SystemSettingsManager.ensure_table()

        existing = SystemSettingsManager.get_setting_record(
            SystemSettingsManager.HEARTBEAT_STALE_GRACE_KEY
        )

        if existing:
            return

        default_seconds = int(
            default_seconds or SystemSettingsManager.DEFAULT_HEARTBEAT_STALE_GRACE_SECONDS
        )
        default_seconds = SystemSettingsManager.validate_heartbeat_stale_grace_seconds(
            default_seconds
        )

        SystemSettingsManager.set_setting(
            setting_key=SystemSettingsManager.HEARTBEAT_STALE_GRACE_KEY,
            setting_value=default_seconds,
            description=(
                "Seconds without GUI heartbeat after which an active browser session is treated as stale. "
                "This protects plant operation when a browser is closed without logout."
            ),
            updated_by="SYSTEM"
        )

    @staticmethod
    def get_heartbeat_stale_grace_seconds():
        SystemSettingsManager.ensure_heartbeat_stale_grace_setting()

        grace_seconds = SystemSettingsManager.get_int(
            setting_key=SystemSettingsManager.HEARTBEAT_STALE_GRACE_KEY,
            default_value=SystemSettingsManager.DEFAULT_HEARTBEAT_STALE_GRACE_SECONDS
        )

        try:
            return SystemSettingsManager.validate_heartbeat_stale_grace_seconds(
                grace_seconds
            )
        except ValueError:
            return SystemSettingsManager.DEFAULT_HEARTBEAT_STALE_GRACE_SECONDS

    @staticmethod
    def set_heartbeat_stale_grace_seconds(grace_seconds, updated_by):
        grace_seconds = SystemSettingsManager.validate_heartbeat_stale_grace_seconds(
            grace_seconds
        )

        SystemSettingsManager.set_setting(
            setting_key=SystemSettingsManager.HEARTBEAT_STALE_GRACE_KEY,
            setting_value=grace_seconds,
            description=(
                "Seconds without GUI heartbeat after which an active browser session is treated as stale. "
                "This protects plant operation when a browser is closed without logout."
            ),
            updated_by=updated_by
        )

        return grace_seconds

    @staticmethod
    def get_session_timeout_minutes():
        SystemSettingsManager.ensure_session_timeout_setting()

        timeout_minutes = SystemSettingsManager.get_int(
            setting_key=SystemSettingsManager.SESSION_TIMEOUT_KEY,
            default_value=SESSION_TIMEOUT_MINUTES
        )

        try:
            return SystemSettingsManager.validate_session_timeout_minutes(
                timeout_minutes
            )
        except ValueError:
            return int(SESSION_TIMEOUT_MINUTES)

    @staticmethod
    def set_session_timeout_minutes(timeout_minutes, updated_by):
        timeout_minutes = SystemSettingsManager.validate_session_timeout_minutes(
            timeout_minutes
        )

        SystemSettingsManager.set_setting(
            setting_key=SystemSettingsManager.SESSION_TIMEOUT_KEY,
            setting_value=timeout_minutes,
            description="Idle auto logout timeout in minutes. Configurable by ADMIN super user from Active Sessions GUI.",
            updated_by=updated_by
        )

        return timeout_minutes
