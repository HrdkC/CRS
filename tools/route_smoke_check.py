import re
import sys
import time
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.safe_runtime_guard import install_safe_runtime_guard
install_safe_runtime_guard()

from app import app
from database.user_session_manager import UserSessionManager


SAMPLE_VALUES = {
    "recipe_id": "12",
    "value_id": "1",
    "parameter_id": "1",
    "machine_id": "5",
    "stage_id": "12",
    "plc_id": "5",
    "family_id": "1",
    "unit_id": "1",
    "machine_code": "P15",
    "stage_code": "SS",
    "job_id": "missing-job",
    "username": "admin",
}


def build_url(rule):
    url = rule.rule
    for arg in sorted(rule.arguments, key=len, reverse=True):
        value = SAMPLE_VALUES.get(arg)
        if value is None:
            return None
        url = re.sub(rf"<(?:[^:<>]+:)?{arg}>", value, url)
    return url


def main():
    app.testing = True
    client = app.test_client()
    session_id, _ = UserSessionManager.login(
        username="admin",
        role="ADMIN",
        client_ip="127.0.0.1",
        workstation_name="CODEX_ROUTE_SMOKE",
        user_agent="route-smoke",
        request_host="localhost",
        login_source="CODEX_ROUTE_SMOKE",
    )
    with client.session_transaction() as sess:
        now = int(time.time())
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["role"] = "ADMIN"
        sess["session_id"] = session_id
        sess["last_activity_epoch"] = now
        sess["last_db_touch_epoch"] = now
        sess["last_login_ist"] = "2026-06-29 00:00:00"
        sess["password_reset_required"] = 0

    failures = []
    checked = 0
    try:
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
            if "GET" not in rule.methods:
                continue
            if rule.endpoint == "static":
                continue
            url = build_url(rule)
            if not url:
                continue
            checked += 1
            try:
                response = client.get(url, follow_redirects=False)
                status = response.status_code
                if status >= 500 or status == 404:
                    failures.append((url, status, "HTTP failure"))
            except Exception as exc:
                failures.append((url, "EXCEPTION", repr(exc)))
                traceback.print_exc()
    finally:
        UserSessionManager.logout(
            session_id,
            reason="CODEX_ROUTE_SMOKE_DONE",
        )

    print(f"checked={checked}")
    for url, status, detail in failures:
        print(f"FAIL {status} {url} {detail}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
