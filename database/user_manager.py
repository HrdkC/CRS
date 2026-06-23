from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database.database import get_connection

from flask_app.security.role_guard import (
    VALID_ROLES
)


class UserManager:

    @staticmethod
    def create_user(
        username,
        password,
        role,
        created_by="SYSTEM"
    ):

        role = role.upper()

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
                created_by
            )
            VALUES
            (?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                role,
                created_by
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

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            AND active = 1
            """,
            (username,)
        )

        user = cursor.fetchone()

        conn.close()

        if not user:
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
                username,
                role,
                active,
                created_at,
                last_login
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

                last_login

            FROM users

            ORDER BY username
            """
        )

        users = cursor.fetchall()

        conn.close()

        return [
            dict(user)
            for user in users
        ]

    @staticmethod
    def disable_user(username):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET active = 0
            WHERE username = ?
            """,
            (username,)
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
            SET active = 1
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
        new_password
    ):

        password_hash = generate_password_hash(
            new_password
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE username = ?
            """,
            (
                password_hash,
                username
            )
        )

        conn.commit()
        conn.close()

        print(
            f"Password Updated : {username}"
        )
        
    @staticmethod
    def update_last_login(
        username
    ):

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
