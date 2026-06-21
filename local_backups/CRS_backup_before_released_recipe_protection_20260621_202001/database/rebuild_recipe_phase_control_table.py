from database.database import (
    get_connection
)


def rebuild_recipe_phase_control_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DROP TABLE IF EXISTS
        recipe_phase_control
        """
    )

    cursor.execute(
        """
        CREATE TABLE
        recipe_phase_control
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            recipe_id INTEGER NOT NULL,

            line_no INTEGER NOT NULL,

            phase_control_id INTEGER,

            stop_option TEXT,

            position_option TEXT,

            sequence_no INTEGER,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(recipe_id)
            REFERENCES recipes(id),

            FOREIGN KEY(phase_control_id)
            REFERENCES phase_control_master(id)
        )
        """
    )

    conn.commit()

    conn.close()

    print(
        "recipe_phase_control rebuilt"
    )


if __name__ == "__main__":

    rebuild_recipe_phase_control_table()
    