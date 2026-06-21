from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    DELETE FROM machine_stages

    WHERE id IN
    (
        9,
        10
    )
    """
)

conn.commit()

conn.close()

print(
    "Duplicate P01 Stages Deleted"
)