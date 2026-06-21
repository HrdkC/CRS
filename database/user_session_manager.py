from database.database import (
    get_connection
)


class UserSessionManager:

    @staticmethod
    def login(

        username,

        client_ip,

        workstation_name

    ):

        conn = get_connection()

        cursor = conn.cursor()

        #
        # Close existing active sessions
        #

        cursor.execute(
            """
            UPDATE user_sessions

            SET logout_time =
            CURRENT_TIMESTAMP

            WHERE username = ?
            AND logout_time IS NULL
            """,
            (
                username,
            )
        )

        #
        # Create new session
        #

        cursor.execute(
            """
            INSERT INTO user_sessions
            (

                username,

                client_ip,

                workstation_name

            )
            VALUES
            (?, ?, ?)
            """,
            (

                username,

                client_ip,

                workstation_name

            )
        )

        conn.commit()

        session_id = cursor.lastrowid

        conn.close()

        return session_id

    @staticmethod
    def logout(

        session_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_sessions

            SET logout_time =
            CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (

                session_id,

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_active_sessions():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                client_ip,
                workstation_name,
                login_time
            FROM user_sessions
            WHERE logout_time IS NULL
            ORDER BY login_time DESC
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]