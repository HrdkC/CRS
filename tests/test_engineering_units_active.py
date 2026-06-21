from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT
        id,
        unit_code,
        description,
        is_active

    FROM engineering_units

    ORDER BY unit_code
    """
)

for row in cursor.fetchall():

    print(
        dict(row)
    )

conn.close()