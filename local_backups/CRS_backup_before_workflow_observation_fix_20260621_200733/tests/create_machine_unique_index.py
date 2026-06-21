from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

try:

    cursor.execute(
        """
        CREATE UNIQUE INDEX
        idx_machine_code_unique

        ON tbm_machines
        (
            UPPER(machine_code)
        )
        """
    )

    print(
        "Machine Unique Index Created"
    )

except Exception as e:

    print(
        f"Already Exists: {e}"
    )

conn.commit()

conn.close()