from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

fields = [

    """
    ALTER TABLE plc_registry
    ADD COLUMN actual_processor_name TEXT
    """,

    """
    ALTER TABLE plc_registry
    ADD COLUMN actual_firmware_revision TEXT
    """,

    """
    ALTER TABLE plc_registry
    ADD COLUMN actual_serial_number TEXT
    """,

    """
    ALTER TABLE plc_registry
    ADD COLUMN actual_program_name TEXT
    """,

    """
    ALTER TABLE plc_registry
    ADD COLUMN verification_status TEXT
    """,

    """
    ALTER TABLE plc_registry
    ADD COLUMN last_verified_at TIMESTAMP
    """

]

for sql in fields:

    try:

        cursor.execute(sql)

    except Exception:

        pass

conn.commit()

conn.close()

print(
    "PLC Verification Fields Added"
)