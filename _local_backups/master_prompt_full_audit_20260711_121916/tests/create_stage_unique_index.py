from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

try:

    cursor.execute(
        """
        CREATE UNIQUE INDEX
        idx_machine_stage_unique

        ON machine_stages
        (
            machine_id,
            stage_type
        )
        """
    )

    print(
        "Unique Index Created"
    )

except Exception as e:

    print(
        f"Already Exists: {e}"
    )

conn.commit()

conn.close()