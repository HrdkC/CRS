from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    DELETE FROM
    parameter_definitions

    WHERE
    parameter_name = 'BEAD_SET'
    """
)

conn.commit()

conn.close()

print(
    "Test Parameter Deleted"
)