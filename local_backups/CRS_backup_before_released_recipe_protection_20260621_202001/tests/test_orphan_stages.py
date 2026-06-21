from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT

        s.id,

        s.machine_id,

        s.stage_type

    FROM machine_stages s

    LEFT JOIN tbm_machines m

    ON s.machine_id = m.id

    WHERE m.id IS NULL
    """
)

rows = cursor.fetchall()

for row in rows:

    print(
        row["id"],
        row["machine_id"],
        row["stage_type"]
    )

conn.close()