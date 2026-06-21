from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    UPDATE user_sessions

    SET logout_time =
    CURRENT_TIMESTAMP

    WHERE logout_time IS NULL
    """
)

conn.commit()

conn.close()

print(
    "All Active Sessions Closed"
)