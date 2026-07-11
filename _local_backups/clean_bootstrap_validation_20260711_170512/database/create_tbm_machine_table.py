from database.database import get_connection


def create_tbm_machine_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tbm_machines
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            machine_code TEXT NOT NULL UNIQUE,

            family_id INTEGER NOT NULL,

            description TEXT,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (family_id)
            REFERENCES tbm_families(id)
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_tbm_machine_table()

    print(
        "TBM Machine Table Created"
    )