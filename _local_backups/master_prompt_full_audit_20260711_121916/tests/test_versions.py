# tests/test_versions.py

from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT DISTINCT version

    FROM recipe_parameters

    WHERE recipe_code = 'GT7107'

    ORDER BY version
    """
)

for row in cursor.fetchall():

    print(
        dict(row)
    )

conn.close()