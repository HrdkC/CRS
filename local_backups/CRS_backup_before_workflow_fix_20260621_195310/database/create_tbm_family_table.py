from database.database import get_connection


def create_tbm_family_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tbm_families
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            family_name TEXT NOT NULL UNIQUE,

            description TEXT,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_tbm_family_table()

    print(
        "TBM Family Table Created"
    )