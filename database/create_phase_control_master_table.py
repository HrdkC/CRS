from database.database import get_connection


def create_phase_control_master_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS phase_control_master
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            stage_type TEXT NOT NULL,

            phase_control_name TEXT NOT NULL,

            phase_control_key TEXT,

            plc_phase_code INTEGER,

            description TEXT,

            display_order INTEGER DEFAULT 0,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            machine_stage_id INTEGER,

            phase_group_code TEXT DEFAULT 'MAIN',

            phase_group_name TEXT DEFAULT 'Phase Control'
        )
        """
    )

    cursor.execute("PRAGMA table_info(phase_control_master)")
    columns = {row["name"] for row in cursor.fetchall()}

    if "phase_control_key" not in columns:
        cursor.execute(
            "ALTER TABLE phase_control_master ADD COLUMN phase_control_key TEXT"
        )

    if "plc_phase_code" not in columns:
        cursor.execute(
            "ALTER TABLE phase_control_master ADD COLUMN plc_phase_code INTEGER"
        )

    if "machine_stage_id" not in columns:
        cursor.execute(
            "ALTER TABLE phase_control_master ADD COLUMN machine_stage_id INTEGER"
        )

    if "phase_group_code" not in columns:
        cursor.execute(
            "ALTER TABLE phase_control_master ADD COLUMN phase_group_code TEXT DEFAULT 'MAIN'"
        )

    if "phase_group_name" not in columns:
        cursor.execute(
            "ALTER TABLE phase_control_master ADD COLUMN phase_group_name TEXT DEFAULT 'Phase Control'"
        )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_phase_control_master_table()

    print(
        "Phase Control Master Table Created"
    )
