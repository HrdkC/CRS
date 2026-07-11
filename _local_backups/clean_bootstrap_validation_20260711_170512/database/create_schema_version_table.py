from database.database import get_connection

def create_schema_version_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            version TEXT NOT NULL,

            description TEXT,

            applied_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_schema_version_table()

    print(
        "Schema Version Table Created"
    )