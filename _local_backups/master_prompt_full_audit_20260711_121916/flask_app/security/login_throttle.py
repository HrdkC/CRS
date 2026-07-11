import os
import time


MAX_FAILURES = int(os.getenv("CRS_LOGIN_MAX_FAILURES", "5"))
LOCKOUT_SECONDS = int(os.getenv("CRS_LOGIN_LOCKOUT_SECONDS", "300"))
WINDOW_SECONDS = int(os.getenv("CRS_LOGIN_FAILURE_WINDOW_SECONDS", "900"))

_attempts = {}


def _key(username, client_ip):
    safe_username = (username or "").strip().lower() or "-"
    safe_ip = (client_ip or "").strip() or "-"
    return f"{safe_username}|{safe_ip}"


def _now():
    return int(time.time())


def _cleanup(now):
    stale_before = now - max(WINDOW_SECONDS, LOCKOUT_SECONDS)
    for key in list(_attempts.keys()):
        record = _attempts[key]
        if int(record.get("last_failed_at", 0)) < stale_before:
            _attempts.pop(key, None)


def is_login_blocked(username, client_ip):
    now = _now()
    _cleanup(now)
    record = _attempts.get(_key(username, client_ip))
    if not record:
        return False, 0

    blocked_until = int(record.get("blocked_until", 0))
    if blocked_until > now:
        return True, blocked_until - now

    return False, 0


def record_login_failure(username, client_ip):
    now = _now()
    key = _key(username, client_ip)
    record = _attempts.get(key, {"count": 0, "first_failed_at": now})

    if now - int(record.get("first_failed_at", now)) > WINDOW_SECONDS:
        record = {"count": 0, "first_failed_at": now}

    record["count"] = int(record.get("count", 0)) + 1
    record["last_failed_at"] = now

    if record["count"] >= MAX_FAILURES:
        record["blocked_until"] = now + LOCKOUT_SECONDS

    _attempts[key] = record


def record_login_success(username, client_ip):
    _attempts.pop(_key(username, client_ip), None)
