from database.database import get_connection


def create_plc_registry_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS plc_registry
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            machine_stage_id INTEGER NOT NULL,

            plc_name TEXT NOT NULL,

            ip_address TEXT NOT NULL,

            controller_type TEXT,

            firmware_revision TEXT,

            program_revision TEXT,

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

    create_plc_registry_table()

    print(
        "PLC Registry Table Created"
    )