from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    ALTER TABLE engineering_units
    ADD COLUMN is_active INTEGER
    DEFAULT 1
    """
)

conn.commit()

conn.close()

print(
    "is_active column added"
)