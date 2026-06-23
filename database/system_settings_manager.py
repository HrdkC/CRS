from config.settings import SESSION_TIMEOUT_MINUTES
from database.database import get_connection


class SystemSettingsManager:
    """Centralized application settings stored in SQLite.

    Environment variables still provide startup defaults, but Admin users can
    adjust selected settings from the GUI. The database value is treated as the
    source of truth after it is created.
    """

    SESSION_TIMEOUT_KEY = "SESSION_TIMEOUT_MINUTES"
    MIN_SESSION_TIMEOUT_MINUTES = 1
    MAX_SESSION_TIMEOUT_MINUTES = 480

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
