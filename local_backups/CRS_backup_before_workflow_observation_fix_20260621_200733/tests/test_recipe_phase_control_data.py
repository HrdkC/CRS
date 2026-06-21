from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT *

    FROM recipe_phase_control

    LIMIT 20
    """
)

rows = cursor.fetchall()

print(
    "ROWS =",
    len(rows)
)

for row in rows:

    print(
        dict(row)
    )

conn.close()