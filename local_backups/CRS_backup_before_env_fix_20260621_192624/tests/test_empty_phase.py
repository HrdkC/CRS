from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute("""
SELECT id,
       phase_control_name

FROM phase_control_master

ORDER BY id
""")

for row in cursor.fetchall():

    print(
        row["id"],
        row["phase_control_name"]
    )

conn.close()