from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    UPDATE tbm_machines

    SET machine_code =
    UPPER(machine_code)
    """
)

conn.commit()

conn.close()

print(
    "Machine Codes Converted To Uppercase"
)