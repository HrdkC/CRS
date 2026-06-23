import os
import sys
from werkzeug.security import generate_password_hash

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.database import get_connection


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _add_column_if_missing(cursor, table_name, column_name, column_definition):
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )
        print(f"Added column: {table_name}.{column_name}")


def upgrade_user_management_schema():
    conn = get_connection()
    cursor = conn.cursor()

    _add_column_if_missing(cursor, "users", "password_reset_required", "INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "users", "password_changed_at", "DATETIME")
    _add_column_if_missing(cursor, "users", "disabled_at", "DATETIME")
    _add_column_if_missing(cursor, "users", "disabled_by", "TEXT")
    _add_column_if_missing(cursor, "users", "role_updated_at", "DATETIME")
    _add_column_if_missing(cursor, "users", "role_updated_by", "TEXT")
    _add_column_if_missing(cursor, "users", "remarks", "TEXT")

    _add_column_if_missing(cursor, "user_sessions", "role", "TEXT")
    _add_column_if_missing(cursor, "user_sessions", "last_activity", "DATETIME")
    _add_column_if_missing(cursor, "user_sessions", "logout_reason", "TEXT")
    _add_column_if_missing(cursor, "user_sessions", "auto_logged_out", "INTEGER DEFAULT 0")

    cursor.execute(
        """
        UPDATE user_sessions
        SET last_activity = COALESCE(last_activity, login_time)
        WHERE last_activity IS NULL
        """
    )

    conn.commit()
    conn.close()

    print("Priority 11 user/session schema upgrade completed.")


def ensure_seed_user(
    username,
    password,
    role,
    created_by="SYSTEM",
    remarks=None,
    force_password_reset=True,
    protect_existing_password=True
):
    """
    Idempotent seed helper for required CRS accounts.

    If the user exists, role/active/reset flags are corrected. By default, the
    existing password is not overwritten to avoid surprising an already-used
    production account.
    """

    username = (username or "").strip()
    role = (role or "").upper().strip()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (username,)
    )

    existing = cursor.fetchone()

    if existing:
        if protect_existing_password:
            cursor.execute(
                """
                UPDATE users
                SET role = ?,
                    active = 1,
                    password_reset_required = ?,
                    role_updated_at = CURRENT_TIMESTAMP,
                    role_updated_by = ?,
                    remarks = COALESCE(remarks, ?)
                WHERE username = ?
                """,
                (
                    role,
                    1 if force_password_reset else 0,
                    created_by,
                    remarks,
                    username
                )
            )
            print(f"Seed user already existed and was enabled: {username} ({role})")
        else:
            cursor.execute(
                """
                UPDATE users
                SET password_hash = ?,
                    role = ?,
                    active = 1,
                    password_reset_required = ?,
                    password_changed_at = CURRENT_TIMESTAMP,
                    role_updated_at = CURRENT_TIMESTAMP,
                    role_updated_by = ?,
                    remarks = COALESCE(remarks, ?)
                WHERE username = ?
                """,
                (
                    generate_password_hash(password),
                    role,
                    1 if force_password_reset else 0,
                    created_by,
                    remarks,
                    username
                )
            )
            print(f"Seed user already existed and password was reset: {username} ({role})")
    else:
        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                password_hash,
                role,
                active,
                created_by,
                password_reset_required,
                password_changed_at,
                remarks
            )
            VALUES
            (?, ?, ?, 1, ?, ?, CURRENT_TIMESTAMP, ?)
            """,
            (
                username,
                generate_password_hash(password),
                role,
                created_by,
                1 if force_password_reset else 0,
                remarks
            )
        )
        print(f"Seed user created: {username} ({role})")

    conn.commit()
    conn.close()


def ensure_default_operator_user(
    username="operator",
    password="operator123",
    created_by="SYSTEM"
):
    ensure_seed_user(
        username=username,
        password=password,
        role="OPERATOR",
        created_by=created_by,
        remarks="Default operator login created by Priority 11 helper. Change password after first login.",
        force_password_reset=True,
        protect_existing_password=True
    )


def ensure_default_engineering_user(
    username="engineering",
    password="Engineering@123",
    created_by="SYSTEM"
):
    ensure_seed_user(
        username=username,
        password=password,
        role="ENGINEERING",
        created_by=created_by,
        remarks="Default engineering user created by Priority 11 helper. Engineering is below Admin and cannot manage users/sessions.",
        force_password_reset=True,
        protect_existing_password=True
    )


def ensure_backup_admin_user(
    username="hardik",
    password="Hardik@123",
    created_by="SYSTEM"
):
    ensure_seed_user(
        username=username,
        password=password,
        role="ADMIN",
        created_by=created_by,
        remarks="Backup CRS super user created by Priority 11 helper. Keep enabled for emergency admin recovery.",
        force_password_reset=True,
        protect_existing_password=True
    )


def ensure_priority11_default_users():
    upgrade_user_management_schema()
    ensure_default_operator_user()
    ensure_default_engineering_user()
    ensure_backup_admin_user()


if __name__ == "__main__":
    upgrade_user_management_schema()
