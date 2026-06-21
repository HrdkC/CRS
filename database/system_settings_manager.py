from database.database import get_connection


class SystemSettingsManager:

    @staticmethod
    def set_setting(

        setting_key,

        setting_value,

        description=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO
            system_settings
            (

                setting_key,

                setting_value,

                description

            )
            VALUES
            (?, ?, ?)
            """,
            (

                setting_key,

                setting_value,

                description

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_setting(

        setting_key,

        default_value=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT setting_value

            FROM system_settings

            WHERE setting_key = ?
            """,
            (
                setting_key,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return row["setting_value"]

        return default_value