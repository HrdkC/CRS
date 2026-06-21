from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

try:

    cursor.execute(
        """
        ALTER TABLE plc_registry

        ADD COLUMN processor_name TEXT
        """
    )

except:

    pass

try:

    cursor.execute(
        """
        ALTER TABLE plc_registry

        ADD COLUMN plc_software TEXT
        """
    )

except:

    pass

try:

    cursor.execute(
        """
        ALTER TABLE plc_registry

        ADD COLUMN last_verified_at TIMESTAMP
        """
    )

except:

    pass

try:

    cursor.execute(
        """
        ALTER TABLE plc_registry

        ADD COLUMN created_by TEXT
        """
    )

except:

    pass

conn.commit()

conn.close()

print(
    "PLC Registry Fields Added"
)