from database.database import (
    get_connection
)


def create_recipe_status_history_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS
        recipe_status_history
        (

            id INTEGER
            PRIMARY KEY AUTOINCREMENT,

            recipe_id INTEGER
            NOT NULL,

            recipe_code TEXT,

            old_status TEXT,

            new_status TEXT,

            changed_by TEXT,

            changed_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    conn.commit()

    conn.close()

    print(
        "recipe_status_history table ready"
    )


if __name__ == "__main__":

    create_recipe_status_history_table()