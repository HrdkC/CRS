from database.database import get_connection


def create_plc_program_history_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS plc_program_history
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            plc_registry_id INTEGER NOT NULL,

            old_program_revision TEXT,

            new_program_revision TEXT,

            old_firmware_revision TEXT,

            new_firmware_revision TEXT,

            change_reason TEXT,

            changed_by TEXT,

            changed_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_plc_program_history_table()

    print(
        "PLC Program History Table Created"
    )