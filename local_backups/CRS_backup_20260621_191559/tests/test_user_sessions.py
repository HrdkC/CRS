from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
"""
SELECT *
FROM user_sessions
ORDER BY id DESC
"""
)

for row in cursor.fetchall():

    print(dict(row))

conn.close()
