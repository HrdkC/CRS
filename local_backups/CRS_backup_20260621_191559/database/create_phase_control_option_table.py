from database.database import get_connection


def create_phase_control_option_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS phase_control_options
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            phase_control_id INTEGER NOT NULL,

            option_code TEXT NOT NULL,

            description TEXT,

            display_order INTEGER DEFAULT 0,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (phase_control_id)
            REFERENCES phase_control_master(id)
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_phase_control_option_table()

    print(
        "Phase Control Option Table Created"
    )