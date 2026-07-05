import sqlite3

DB_PATH = r"database\recipe.db"
REASON = "MANUAL_CLEAR_STALE_SESSION_AFTER_DEV_RESTART"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(user_sessions)")
    columns = [row[1] for row in cur.fetchall()]

    if not columns:
        print("ERROR: user_sessions table not found.")
        conn.close()
        return

    print("user_sessions columns:")
    print(columns)

    set_parts = []
    params = []

    # Mark inactive if such column exists
    if "is_active" in columns:
        set_parts.append("is_active = 0")

    if "active" in columns:
        set_parts.append("active = 0")

    # Close session timestamp
    if "logout_time" in columns:
        set_parts.append("logout_time = CURRENT_TIMESTAMP")

    if "logout_reason" in columns:
        set_parts.append("logout_reason = ?")
        params.append(REASON)

    if "auto_logged_out" in columns:
        set_parts.append("auto_logged_out = 0")

    if "status" in columns:
        set_parts.append("status = 'CLOSED'")

    if "session_status" in columns:
        set_parts.append("session_status = 'CLOSED'")

    if not set_parts:
        print("ERROR: Could not find session close columns.")
        conn.close()
        return

    # Detect active sessions based on available schema
    where_parts = []

    if "is_active" in columns:
        where_parts.append("COALESCE(is_active, 0) = 1")

    if "active" in columns:
        where_parts.append("COALESCE(active, 0) = 1")

    if "logout_time" in columns:
        where_parts.append("logout_time IS NULL")

    if "status" in columns:
        where_parts.append("UPPER(COALESCE(status, '')) IN ('ACTIVE', 'OPEN')")

    if "session_status" in columns:
        where_parts.append("UPPER(COALESCE(session_status, '')) IN ('ACTIVE', 'OPEN')")

    if not where_parts:
        print("ERROR: Could not detect active session condition.")
        conn.close()
        return

    sql = f"""
        UPDATE user_sessions
        SET {", ".join(set_parts)}
        WHERE {" OR ".join(where_parts)}
    """

    cur.execute(sql, params)
    rows = cur.rowcount

    conn.commit()
    conn.close()

    print(f"Closed stale active sessions: {rows}")


if __name__ == "__main__":
    main()