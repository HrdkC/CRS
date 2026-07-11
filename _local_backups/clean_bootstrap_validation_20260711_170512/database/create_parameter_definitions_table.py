from database.database import (
    get_connection
)


def create_parameter_definitions_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DROP TABLE IF EXISTS
        parameter_definitions
        """
    )

    cursor.execute(
        """
        CREATE TABLE parameter_definitions
        (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            machine_id INTEGER NOT NULL,

            stage_id INTEGER NOT NULL,

            tag_index INTEGER NOT NULL,

            plc_array_index INTEGER,

            parameter_name TEXT NOT NULL,

            parameter_class TEXT,

            unit TEXT,

            min_value REAL,

            max_value REAL,

            default_value REAL,

            datatype TEXT DEFAULT 'REAL',

            english_memo TEXT,

            used INTEGER DEFAULT 1,

            created_by TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP

        )
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX
        idx_parameter_definition_tag_index

        ON parameter_definitions
        (
            machine_id,
            stage_id,
            tag_index
        )
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX
        idx_parameter_definition_name

        ON parameter_definitions
        (
            machine_id,
            stage_id,
            parameter_name
        )
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX
        idx_parameter_definition_plc_array

        ON parameter_definitions
        (
            machine_id,
            stage_id,
            plc_array_index
        )
        """
    )

    conn.commit()

    conn.close()

    print(
        "Parameter Definitions Table Recreated"
    )


if __name__ == "__main__":

    create_parameter_definitions_table()