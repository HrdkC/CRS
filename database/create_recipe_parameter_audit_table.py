from database.database import (
    get_connection
)


def create_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS
        recipe_parameter_audit
        (

            id INTEGER
            PRIMARY KEY AUTOINCREMENT,

            recipe_id INTEGER
            NOT NULL,

            recipe_parameter_value_id INTEGER
            NOT NULL,

            parameter_definition_id INTEGER
            NOT NULL,

            old_value REAL,

            new_value REAL,

            changed_by TEXT,

            recipe_code TEXT,

            recipe_version INTEGER,

            parameter_name TEXT,

            tag_index INTEGER,

            change_source TEXT DEFAULT 'DATABASE',

            change_reason TEXT,

            user_role TEXT,

            client_ip TEXT,

            workstation_name TEXT,

            changed_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    conn.commit()

    conn.close()

    print(
        "Recipe Parameter Audit Table Created"
    )


if __name__ == "__main__":

    create_table()