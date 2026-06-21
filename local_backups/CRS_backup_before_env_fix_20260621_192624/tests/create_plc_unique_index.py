from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

try:

    cursor.execute(
        """
        CREATE UNIQUE INDEX
        idx_plc_name_unique

        ON plc_registry
        (
            UPPER(plc_name)
        )
        """
    )

    print(
        "PLC Unique Index Created"
    )

except Exception as e:

    print(
        f"Already Exists: {e}"
    )

conn.commit()

conn.close()