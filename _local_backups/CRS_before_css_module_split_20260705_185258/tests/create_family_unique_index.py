from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

try:

    cursor.execute(
        """
        CREATE UNIQUE INDEX
        idx_family_name_unique

        ON tbm_families
        (
            UPPER(family_name)
        )
        """
    )

    print(
        "Family Unique Index Created"
    )

except Exception as e:

    print(
        f"Already Exists: {e}"
    )

conn.commit()

conn.close()