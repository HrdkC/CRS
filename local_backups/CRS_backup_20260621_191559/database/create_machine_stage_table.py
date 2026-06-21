from database.database import get_connection


def create_machine_stage_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_stages
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            machine_id INTEGER NOT NULL,

            stage_type TEXT NOT NULL,

            description TEXT,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (machine_id)
            REFERENCES tbm_machines(id)
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_machine_stage_table()

    print(
        "Machine Stage Table Created"
    )