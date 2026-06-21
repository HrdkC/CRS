from database.database import get_connection


def create_template_parameter_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS template_parameters
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            template_id INTEGER NOT NULL,

            parameter_name TEXT NOT NULL,

            parameter_description TEXT,

            plc_tag TEXT NOT NULL,

            array_index INTEGER,

            data_type TEXT NOT NULL,

            engineering_unit_id INTEGER,

            minimum_value TEXT,

            maximum_value TEXT,

            default_value TEXT DEFAULT '0',

            required_flag INTEGER DEFAULT 1,

            validation_required INTEGER DEFAULT 1,

            critical_parameter INTEGER DEFAULT 0,

            change_reason_required INTEGER DEFAULT 0,

            display_order INTEGER DEFAULT 0,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (template_id)
            REFERENCES template_master(id),

            FOREIGN KEY (engineering_unit_id)
            REFERENCES engineering_units(id)
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_template_parameter_table()

    print(
        "Template Parameter Table Created"
    )