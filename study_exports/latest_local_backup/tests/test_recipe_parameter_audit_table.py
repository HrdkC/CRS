from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    PRAGMA table_info(
        recipe_parameter_audit
    )
    """
)

rows = cursor.fetchall()

for row in rows:

    print(
        dict(row)
    )

conn.close()