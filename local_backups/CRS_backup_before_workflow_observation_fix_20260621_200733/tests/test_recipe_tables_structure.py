from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

tables = [
    "recipe_master",
    "recipe_versions",
    "recipe_parameters"
]

for table in tables:

    print("\n" + "=" * 50)
    print(table.upper())
    print("=" * 50)

    cursor.execute(
        f"PRAGMA table_info({table})"
    )

    columns = cursor.fetchall()

    for column in columns:

        print(
            column["name"],
            "-",
            column["type"]
        )

conn.close()