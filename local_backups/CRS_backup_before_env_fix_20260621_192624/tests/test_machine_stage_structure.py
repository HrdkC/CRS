from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    PRAGMA table_info(
        machine_stages
    )
    """
)

columns = cursor.fetchall()

print()

print("=" * 50)

print(
    "MACHINE_STAGES"
)

print("=" * 50)

for column in columns:

    print(
        f"{column['name']} - {column['type']}"
    )

conn.close()