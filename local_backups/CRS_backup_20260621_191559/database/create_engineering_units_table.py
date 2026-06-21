from database.database import get_connection


def create_engineering_units_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS engineering_units
        (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            unit_code TEXT UNIQUE NOT NULL,

            description TEXT,

            created_at DATETIME
            DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    conn.commit()

    conn.close()

    print(
        "engineering_units table created"
    )


if __name__ == "__main__":

    create_engineering_units_table()