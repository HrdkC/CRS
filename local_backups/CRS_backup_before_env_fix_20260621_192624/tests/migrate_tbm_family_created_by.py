from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
"""
ALTER TABLE tbm_families

ADD COLUMN created_by TEXT
"""

)

conn.commit()

conn.close()

print(
"created_by column added"
)
