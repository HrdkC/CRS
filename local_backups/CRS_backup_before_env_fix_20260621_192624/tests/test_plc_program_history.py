from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT name

    FROM sqlite_master

    WHERE type='table'

    AND name='plc_program_history'
    """
)

row = cursor.fetchone()

if row:

    print(
        "plc_program_history EXISTS"
    )

else:

    print(
        "plc_program_history NOT FOUND"
    )

conn.close()