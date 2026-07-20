import os

from database.database import get_connection, transaction
from database.hardening_schema_manager import assert_v11_11_hardening_schema_ready


MAX_FAILURES = int(os.getenv("CRS_LOGIN_MAX_FAILURES", "5"))
LOCKOUT_SECONDS = int(os.getenv("CRS_LOGIN_LOCKOUT_SECONDS", "300"))
WINDOW_SECONDS = int(os.getenv("CRS_LOGIN_FAILURE_WINDOW_SECONDS", "900"))


def _parts(username, client_ip):
    username_key = (username or "").strip().lower() or "-"
    safe_ip = (client_ip or "").strip() or "-"
    return username_key, safe_ip


def _ensure_schema():
    assert_v11_11_hardening_schema_ready()


def is_login_blocked(username, client_ip):
    _ensure_schema()
    username_key, safe_ip = _parts(username, client_ip)
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                CASE
                    WHEN blocked_until IS NOT NULL
                     AND datetime(blocked_until) > datetime('now')
                    THEN 1 ELSE 0
                END AS blocked,
                MAX(0, CAST(strftime('%s', blocked_until) AS INTEGER)
                    - CAST(strftime('%s', 'now') AS INTEGER)) AS remaining
            FROM login_throttle
            WHERE username_key=? AND client_ip=?
            """,
            (username_key, safe_ip),
        ).fetchone()
        if not row:
            return False, 0
        return bool(row["blocked"]), int(row["remaining"] or 0)
    finally:
        conn.close()


def record_login_failure(username, client_ip):
    _ensure_schema()
    username_key, safe_ip = _parts(username, client_ip)
    with transaction(immediate=True) as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            """
            SELECT * FROM login_throttle
            WHERE username_key=? AND client_ip=?
            """,
            (username_key, safe_ip),
        ).fetchone()

        if not row:
            failure_count = 1
            first_failure_at = "CURRENT_TIMESTAMP"
            cursor.execute(
                """
                INSERT INTO login_throttle
                (username_key, client_ip, failure_count, first_failure_at,
                 last_failure_at, blocked_until, updated_at)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL,
                        CURRENT_TIMESTAMP)
                """,
                (username_key, safe_ip),
            )
        else:
            within_window = cursor.execute(
                """
                SELECT datetime(first_failure_at) >= datetime('now', ?)
                FROM login_throttle
                WHERE username_key=? AND client_ip=?
                """,
                (f"-{max(1, WINDOW_SECONDS)} seconds", username_key, safe_ip),
            ).fetchone()[0]
            failure_count = int(row["failure_count"] or 0) + 1 if within_window else 1
            cursor.execute(
                """
                UPDATE login_throttle
                SET failure_count=?,
                    first_failure_at=CASE WHEN ?=1 THEN CURRENT_TIMESTAMP ELSE first_failure_at END,
                    last_failure_at=CURRENT_TIMESTAMP,
                    blocked_until=NULL,
                    updated_at=CURRENT_TIMESTAMP
                WHERE username_key=? AND client_ip=?
                """,
                (failure_count, 1 if not within_window else 0, username_key, safe_ip),
            )

        if failure_count >= MAX_FAILURES:
            cursor.execute(
                """
                UPDATE login_throttle
                SET blocked_until=datetime('now', ?), updated_at=CURRENT_TIMESTAMP
                WHERE username_key=? AND client_ip=?
                """,
                (f"+{max(1, LOCKOUT_SECONDS)} seconds", username_key, safe_ip),
            )


def record_login_success(username, client_ip):
    _ensure_schema()
    username_key, safe_ip = _parts(username, client_ip)
    with transaction(immediate=True) as conn:
        conn.execute(
            "DELETE FROM login_throttle WHERE username_key=? AND client_ip=?",
            (username_key, safe_ip),
        )
