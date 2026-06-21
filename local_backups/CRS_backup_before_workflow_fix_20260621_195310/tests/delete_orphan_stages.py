from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    DELETE FROM machine_stages

    WHERE machine_id NOT IN
    (
        SELECT id
        FROM tbm_machines
    )
    """
)

conn.commit()

conn.close()

print(
    "Orphan Stages Deleted"
)