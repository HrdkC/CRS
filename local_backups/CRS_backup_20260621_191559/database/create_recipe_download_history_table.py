from database.database import (
    get_connection
)


def create_recipe_download_history_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS
        recipe_download_history
        (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            recipe_id INTEGER NOT NULL,

            recipe_code TEXT,

            recipe_version INTEGER,

            plc_id INTEGER,

            plc_name TEXT,

            downloaded_by TEXT,

            download_start_time TIMESTAMP,

            download_end_time TIMESTAMP,

            download_status TEXT,

            download_message TEXT

        )
        """
    )

    conn.commit()

    conn.close()

    print(
        "recipe_download_history created"
    )