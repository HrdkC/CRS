from database.database import get_connection


def create_phase_control_mapping_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS phase_control_mapping
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            machine_stage_id INTEGER NOT NULL,

            phase_control_id INTEGER NOT NULL,

            plc_tag TEXT NOT NULL,

            array_index INTEGER,

            plc_data_type TEXT NOT NULL,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (machine_stage_id)
            REFERENCES machine_stages(id),

            FOREIGN KEY (phase_control_id)
            REFERENCES phase_control_master(id)
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_phase_control_mapping_table()

    print(
        "Phase Control Mapping Table Created"
    )