from database.database import get_connection


def upgrade_recipes_test_only():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(recipes)")

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "is_test_only" not in columns:

        cursor.execute(
            """
            ALTER TABLE recipes
            ADD COLUMN is_test_only INTEGER DEFAULT 0
            """
        )

        print("Added recipes.is_test_only")

    conn.commit()
    conn.close()


if __name__ == "__main__":

    upgrade_recipes_test_only()
