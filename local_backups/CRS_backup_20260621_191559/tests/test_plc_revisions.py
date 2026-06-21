from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT

        id,

        plc_name,

        program_revision

    FROM plc_registry
    """
)

rows = cursor.fetchall()

for row in rows:

    print(
        dict(row)
    )

conn.close()