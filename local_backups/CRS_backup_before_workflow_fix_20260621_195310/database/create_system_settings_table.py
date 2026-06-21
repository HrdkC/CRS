from database.database import get_connection


def create_system_settings_table():

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

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_system_settings_table()

    print(
        "System Settings Table Created"
    )