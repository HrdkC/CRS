from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    DELETE FROM
    recipe_phase_control
    """
)

conn.commit()

conn.close()

print(
    "All Phase Rows Deleted"
)