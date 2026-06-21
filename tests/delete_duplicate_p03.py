from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    DELETE FROM tbm_machines

    WHERE id = 4
    """
)

conn.commit()

conn.close()

print(
    "Duplicate Machine Deleted"
)