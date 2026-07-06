from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    UPDATE plc_tags

    SET

        array_start_index = 0,

        array_end_index = 499,

        array_size = 500

    WHERE

        tag_name = 'CRS_Recipe_Data'
    """
)

conn.commit()

print(
    "CRS Array Updated"
)

conn.close()