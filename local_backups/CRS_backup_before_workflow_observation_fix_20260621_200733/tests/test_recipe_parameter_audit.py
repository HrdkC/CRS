from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT *

    FROM recipe_parameter_audit

    ORDER BY id DESC
    """
)

rows = cursor.fetchall()

print()

print(
    "ROWS =",
    len(rows)
)

print()

for row in rows:

    print(
        dict(row)
    )

conn.close()