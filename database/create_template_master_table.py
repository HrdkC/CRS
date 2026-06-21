from database.database import get_connection


def create_template_master_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS template_master
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            machine_stage_id INTEGER NOT NULL,

            template_name TEXT NOT NULL,

            template_version INTEGER DEFAULT 1,

            description TEXT,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (machine_stage_id)
            REFERENCES machine_stages(id)
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_template_master_table()

    print(
        "Template Master Table Created"
    )