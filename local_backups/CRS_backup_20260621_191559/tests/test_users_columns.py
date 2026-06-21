from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    PRAGMA table_info(users)
    """
)

for row in cursor.fetchall():

    print(
        dict(row)
    )

conn.close()