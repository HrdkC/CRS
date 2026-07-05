from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database.database import get_connection

from flask_app.security.role_guard import (
    VALID_ROLES,
    FINAL_ROLES
)


class UserManager:

    @staticmethod
    def create_user(
        username,
        password,
        role,
        created_by="SYSTEM",
        password_reset_required=1,
        remarks=None
    ):
        username = (username or "").strip()
        role = (role or "").upper().strip()

        if not username:
            print("Username required")
            return False

        if role not in VALID_ROLES:
            print("Invalid Role")
            return False

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

        if cursor.fetchone():
            print("Username already exists")
            conn.close()
            return False

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                password_hash,
                role,
                created_by,
                password_reset_required,
                password_changed_at,
                remarks
            )
            VALUES
            (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """,
            (
                username,
                password_hash,
                role,
                created_by,
                1 if password_reset_required else 0,
                remarks
            )
        )

        conn.commit()
        conn.close()

        print(f"User Created : {username}")
        return True

    @staticmethod
    def verify_user(
        username,
        password
    ):
        user = UserManager.get_user(username)

        if not user or user.get("active") != 1:
            return False

        return check_password_hash(
            user["password_hash"],
            password
        )

    @staticmethod
    def get_user(username):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                password_hash,
                role,
                active,
                created_by,
                created_at,
                last_login,
                password_reset_required,
                password_changed_at,
                disabled_at,
                disabled_by,
                role_updated_at,
                role_updated_by,
                remarks
            FROM users
            WHERE username = ?
            """,
            (username,)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            return dict(user)

        return None

    @staticmethod
    def list_users():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                username,
                role,
                active,
                created_by,
                created_at,
                last_login,
                password_reset_required,
                password_changed_at,
                disabled_at,
                disabled_by,
                role_updated_at,
                role_updated_by,
                remarks
            FROM users
            ORDER BY
                CASE role
                    WHEN 'ADMIN' THEN 1
                    WHEN 'ENGINEERING' THEN 2
                    WHEN 'TECHNOLOGY' THEN 3
                    WHEN 'PRODUCTION' THEN 4
                    WHEN 'OPERATOR' THEN 5
                    WHEN 'VIEWER' THEN 6
                    ELSE 9
                END,
                username
            """
        )

        users = cursor.fetchall()
        conn.close()

        return [dict(user) for user in users]

    @staticmethod
    def disable_user(
        username,
        disabled_by=None
    ):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET active = 0,
                disabled_at = CURRENT_TIMESTAMP,
                disabled_by = ?
            WHERE username = ?
            """,
            (disabled_by, username)
        )

        conn.commit()
        conn.close()

        print(f"User Disabled : {username}")

    @staticmethod
    def enable_user(username):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET active = 1,
                disabled_at = NULL,
                disabled_by = NULL
            WHERE username = ?
            """,
            (username,)
        )

        conn.commit()
        conn.close()

        print(f"User Enabled : {username}")

    @staticmethod
    def change_password(
        username,
        new_password,
        require_reset=False
    ):
        password_hash = generate_password_hash(new_password)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?,
                password_changed_at = CURRENT_TIMESTAMP,
                password_reset_required = ?
            WHERE username = ?
            """,
            (
                password_hash,
                1 if require_reset else 0,
                username
            )
        )

        conn.commit()
        conn.close()

        print(f"Password Updated : {username}")

    @staticmethod
    def mark_password_reset_required(
        username,
        required=True
    ):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET password_reset_required = ?
            WHERE username = ?
            """,
            (1 if required else 0, username)
        )

        conn.commit()
        conn.close()

    @staticmethod
    def update_role(
        username,
        role,
        updated_by="SYSTEM"
    ):
        role = (role or "").upper().strip()

        if role not in FINAL_ROLES:
            print("Invalid final CRS role")
            return False

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET role = ?,
                role_updated_at = CURRENT_TIMESTAMP,
                role_updated_by = ?
            WHERE username = ?
            """,
            (role, updated_by, username)
        )

        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()

        if updated:
            print(f"Role Updated : {username} -> {role}")

        return updated

    @staticmethod
    def update_last_login(username):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE username = ?
            """,
            (username,)
        )

        conn.commit()
        conn.close()

    @staticmethod
    def active_admin_count():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            WHERE role = 'ADMIN'
              AND active = 1
            """
        )

        row = cursor.fetchone()
        conn.close()

        return int(row["total"] if row else 0)

    @staticmethod
    def is_last_active_admin(username):
        user = UserManager.get_user(username)

        if not user:
            return False

        if user.get("role") != "ADMIN" or user.get("active") != 1:
            return False

        return UserManager.active_admin_count() <= 1

    @staticmethod
    def role_summary():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role, COUNT(*) AS total
            FROM users
            GROUP BY role
            ORDER BY role
            """
        )

        rows = cursor.fetchall()
        conn.close()

        return {row["role"]: row["total"] for row in rows}
