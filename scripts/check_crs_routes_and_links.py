"""Safe CRS route/template/link smoke test.

This checker does not write PLC values and deliberately skips live PLC connection
and download-start endpoints. It uses Flask's test client against the current
project database, renders safe GET pages, compiles all Jinja templates, and
verifies rendered internal links and form actions against the Flask route map.
"""

from __future__ import annotations

import os
import py_compile
import sys
import time
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

# Prevent schema/data startup mutations during a verification run.
os.environ.setdefault("CRS_ALLOW_STARTUP_MIGRATIONS", "0")
os.environ.setdefault("CRS_FLASK_DEBUG", "0")
os.environ.setdefault("CRS_FLASK_RELOAD", "0")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import url_for  # noqa: E402
from werkzeug.exceptions import MethodNotAllowed, NotFound  # noqa: E402

import app as app_module  # noqa: E402
from database.database import get_connection  # noqa: E402
from database.user_session_manager import UserSessionManager  # noqa: E402


EXCLUDED_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "venv",
    ".venv",
    "local_backups",
    "_local_backups",
    "study_exports",
}

# These endpoints intentionally perform live PLC/network or asynchronous write work.
UNSAFE_GET_ENDPOINTS = {
    "test_connection",
    "verify_plc",
}

# A synthetic job id is expected to return 404 and is not a broken page.
EXPECTED_404_ENDPOINTS = {
    "recipe_download_preparation_job_status",
}


class _HtmlTargetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.forms: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "form":
            self.forms.append(
                (
                    str(values.get("method") or "GET").upper(),
                    str(values.get("action") or ""),
                )
            )


def _iter_project_python_files():
    for path in PROJECT_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        yield path


def _scalar(sql: str, params=(), default=None):
    conn = get_connection()
    try:
        row = conn.execute(sql, params).fetchone()
        if not row:
            return default
        return row[0]
    except Exception:
        return default
    finally:
        conn.close()


def _sample_values() -> dict[str, object]:
    machine_id = _scalar(
        "SELECT machine_id FROM parameter_definitions ORDER BY id LIMIT 1",
        default=1,
    )
    stage_id = _scalar(
        "SELECT stage_id FROM parameter_definitions ORDER BY id LIMIT 1",
        default=1,
    )

    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT m.machine_code, s.stage_type
            FROM machine_stages s
            JOIN tbm_machines m ON m.id = s.machine_id
            WHERE s.id = ?
            """,
            (stage_id,),
        ).fetchone()
        machine_code = row[0] if row else "P15"
        stage_type = row[1] if row else "FIRST_STAGE"
    finally:
        conn.close()

    stage_code = "SS" if str(stage_type).upper() == "SECOND_STAGE" else "FS"
    recipe_id = _scalar("SELECT id FROM recipes ORDER BY id LIMIT 1", default=1)
    recipe_code = _scalar(
        "SELECT recipe_code FROM recipes WHERE id = ?",
        (recipe_id,),
        default="GT_TEST_001",
    )
    parameter_id = _scalar(
        "SELECT id FROM parameter_definitions ORDER BY id LIMIT 1",
        default=1,
    )
    parameter_name = _scalar(
        "SELECT parameter_name FROM parameter_definitions WHERE id = ?",
        (parameter_id,),
        default="Parameter",
    )

    return {
        "machine_code": machine_code,
        "stage_code": stage_code,
        "stage_path": stage_code,
        "machine_id": machine_id,
        "stage_id": stage_id,
        "recipe_id": recipe_id,
        "recipe_code": recipe_code,
        "parameter_id": parameter_id,
        "parameter_name": parameter_name,
        "value_id": _scalar(
            "SELECT id FROM recipe_parameter_values ORDER BY id LIMIT 1",
            default=1,
        ),
        "version_id": _scalar(
            "SELECT id FROM recipe_versions ORDER BY id LIMIT 1",
            default=1,
        ),
        "unit_id": _scalar(
            "SELECT id FROM engineering_units ORDER BY id LIMIT 1",
            default=1,
        ),
        "family_id": _scalar(
            "SELECT id FROM tbm_families ORDER BY id LIMIT 1",
            default=1,
        ),
        "tag_id": _scalar("SELECT id FROM plc_tags ORDER BY id LIMIT 1", default=1),
        "array_index": 0,
        "plc_id": _scalar("SELECT id FROM plc_registry ORDER BY id LIMIT 1", default=1),
        "username": _scalar(
            "SELECT username FROM users WHERE role = 'ADMIN' AND active = 1 ORDER BY id LIMIT 1",
            default="admin",
        ),
        "topic_key": "user-manual",
        "job_id": "CRS_ROUTE_SMOKE_NONEXISTENT_JOB",
        "status": "DRAFT",
        "alert_id": 1,
        "session_id": 1,
    }


def _cleanup_test_session(session_id: int | None) -> None:
    if not session_id:
        return
    conn = get_connection()
    try:
        conn.execute("DELETE FROM user_sessions WHERE id = ?", (session_id,))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def main() -> int:
    app = app_module.app
    values = _sample_values()
    failures: list[str] = []
    warnings: list[str] = []

    print("[1/5] Python compile check")
    compiled = 0
    for path in _iter_project_python_files():
        try:
            py_compile.compile(str(path), doraise=True)
            compiled += 1
        except Exception as exc:
            failures.append(f"PYTHON COMPILE: {path.relative_to(PROJECT_ROOT)}: {exc}")
    print(f"  Compiled {compiled} Python file(s).")

    print("[2/5] Jinja template compile check")
    templates = 0
    for template_name in app.jinja_env.list_templates():
        try:
            app.jinja_env.get_template(template_name)
            templates += 1
        except Exception as exc:
            failures.append(f"JINJA: {template_name}: {exc}")
    print(f"  Compiled {templates} template(s).")

    print("[3/5] Route map duplicate check")
    route_keys: dict[tuple[str, str], str] = {}
    for rule in app.url_map.iter_rules():
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            key = (rule.rule, method)
            existing = route_keys.get(key)
            if existing and existing != rule.endpoint:
                failures.append(
                    f"DUPLICATE ROUTE: {method} {rule.rule}: {existing} and {rule.endpoint}"
                )
            route_keys[key] = rule.endpoint
    print(f"  Checked {len(route_keys)} route/method combination(s).")

    test_session_id = None
    rendered_pages: list[tuple[str, str]] = []
    status_counter: Counter[str] = Counter()

    try:
        test_session_id, _ = UserSessionManager.login(
            username=str(values["username"]),
            client_ip="127.0.0.1",
            workstation_name="CRS_ROUTE_SMOKE_TEST",
            role="ADMIN",
            user_agent="CRS safe route checker",
            forwarded_for=None,
            request_host="localhost",
            login_source="SAFE_ROUTE_SMOKE_TEST",
        )
        values["session_id"] = test_session_id

        client = app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update(
                logged_in=True,
                username=str(values["username"]),
                role="ADMIN",
                session_id=test_session_id,
                last_activity_epoch=int(time.time()),
                last_db_touch_epoch=int(time.time()),
                password_reset_required=0,
            )

        print("[4/5] Safe GET page smoke check")
        with app.test_request_context():
            for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
                methods = rule.methods - {"HEAD", "OPTIONS"}
                if "GET" not in methods or rule.endpoint == "static":
                    continue
                if rule.endpoint in UNSAFE_GET_ENDPOINTS:
                    warnings.append(f"SKIPPED LIVE PLC GET: {rule.rule}")
                    continue

                kwargs = {name: values.get(name) for name in rule.arguments}
                if any(value is None for value in kwargs.values()):
                    warnings.append(
                        f"SKIPPED NO SAMPLE: {rule.endpoint} {sorted(rule.arguments)}"
                    )
                    continue

                try:
                    target = url_for(rule.endpoint, **kwargs)
                except Exception as exc:
                    failures.append(f"URL BUILD: {rule.endpoint}: {exc}")
                    continue

                try:
                    response = client.get(target, follow_redirects=False)
                except Exception as exc:
                    failures.append(f"GET EXCEPTION: {target}: {type(exc).__name__}: {exc}")
                    continue

                status_counter[str(response.status_code)] += 1
                if response.status_code >= 500:
                    failures.append(f"GET {target}: HTTP {response.status_code}")
                    continue
                if response.status_code == 404 and rule.endpoint not in EXPECTED_404_ENDPOINTS:
                    failures.append(f"GET {target}: unexpected HTTP 404")
                    continue
                if response.status_code == 405:
                    failures.append(f"GET {target}: HTTP 405")
                    continue

                if response.status_code == 200 and "text/html" in response.content_type:
                    rendered_pages.append((target, response.get_data(as_text=True)))

        print(
            "  Status counts: "
            + ", ".join(f"{key}={value}" for key, value in sorted(status_counter.items()))
        )

        print("[5/5] Rendered internal link/form action check")
        adapter = app.url_map.bind("localhost")
        checked_targets: set[tuple[str, str, str]] = set()
        link_count = 0
        form_count = 0

        for source_url, html in rendered_pages:
            parser = _HtmlTargetParser()
            parser.feed(html)

            targets = [("LINK", "GET", value) for value in parser.links]
            targets.extend(("FORM", method, action) for method, action in parser.forms)

            for kind, method, raw_target in targets:
                if kind == "LINK":
                    link_count += 1
                else:
                    form_count += 1

                if not raw_target or raw_target.startswith(
                    ("#", "javascript:", "mailto:", "tel:", "http://", "https://", "//")
                ):
                    continue

                path = urlsplit(raw_target).path or "/"
                identity = (kind, method, path)
                if identity in checked_targets:
                    continue
                checked_targets.add(identity)

                try:
                    adapter.match(path, method=method)
                except MethodNotAllowed as exc:
                    failures.append(
                        f"{source_url}: {kind} {method} {raw_target}: HTTP 405; "
                        f"allowed={sorted(exc.valid_methods or [])}"
                    )
                except NotFound:
                    failures.append(
                        f"{source_url}: {kind} {method} {raw_target}: no matching route"
                    )
                except Exception as exc:
                    failures.append(
                        f"{source_url}: {kind} {method} {raw_target}: {type(exc).__name__}: {exc}"
                    )

        print(
            f"  Parsed {link_count} rendered link(s), {form_count} form(s), "
            f"{len(checked_targets)} unique internal target(s)."
        )

    finally:
        _cleanup_test_session(test_session_id)

    print("\nCRS SAFE ROUTE CHECK RESULT")
    if warnings:
        print(f"Warnings/skips: {len(warnings)}")
        for item in warnings:
            print(f"  - {item}")

    if failures:
        print(f"FAILED: {len(failures)} problem(s)")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: No Python, Jinja, safe-page HTTP 500, broken rendered link, or form-action issue found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
