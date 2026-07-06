from database.database import get_connection


def create_recipe_versions_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS recipe_versions
        (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            recipe_code TEXT NOT NULL,

            version INTEGER NOT NULL,

            created_by TEXT,

            created_at DATETIME
            DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_recipe_versions_table()

    print(
        "recipe_versions created"
    )