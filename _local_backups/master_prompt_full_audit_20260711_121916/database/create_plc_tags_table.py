from database.database import (
    get_connection
)


def create_plc_tags_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS plc_tags
        (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            machine_id INTEGER NOT NULL,

            stage_id INTEGER NOT NULL,

            tag_name TEXT NOT NULL,

            tag_type TEXT,

            is_array INTEGER DEFAULT 0,

            array_size INTEGER,

            array_start_index INTEGER,

            array_end_index INTEGER,

            description TEXT,

            created_by TEXT,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_plc_tag_unique

        ON plc_tags
        (
            machine_id,
            stage_id,
            tag_name
        )
        """
    )

    conn.commit()

    conn.close()

    print(
        "PLC Tags Table Created"
    )


if __name__ == "__main__":

    create_plc_tags_table()