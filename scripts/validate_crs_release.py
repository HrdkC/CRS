"""Run safe, no-PLC CRS release checks and write an evidence report."""

from __future__ import annotations

import argparse
import compileall
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.exceptions import MethodNotAllowed, NotFound


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEMPLATE_ROOT = PROJECT_ROOT / "flask_app" / "templates"
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
DATABASE_PATH = PROJECT_ROOT / "database" / "recipe.db"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "validation"


def _check(name, passed, detail, severity="required"):
    return {
        "name": name,
        "passed": bool(passed),
        "detail": str(detail),
        "severity": severity,
    }


def _database_checks():
    if not DATABASE_PATH.exists():
        return [
            _check("SQLite database exists", False, DATABASE_PATH)
        ]

    uri = f"file:{DATABASE_PATH.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        return [
            _check("SQLite integrity", integrity == "ok", integrity),
            _check(
                "SQLite foreign keys",
                not foreign_keys,
                f"{len(foreign_keys)} violation(s)",
            ),
        ]
    finally:
        connection.close()


def _css_checks():
    checks = []
    main_path = CSS_ROOT / "main.css"
    main_source = main_path.read_text(encoding="utf-8")
    imports = re.findall(r'@import\s+url\(["\']?([^"\')?]+)', main_source)
    missing = []
    for import_path in imports:
        clean_path = import_path.split("?", 1)[0]
        if not (CSS_ROOT / clean_path).exists():
            missing.append(clean_path)
    checks.append(
        _check(
            "CSS module imports",
            not missing,
            "all imports resolve" if not missing else f"missing: {missing}",
        )
    )

    brace_errors = []
    for path in CSS_ROOT.rglob("*.css"):
        source = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
        if source.count("{") != source.count("}"):
            brace_errors.append(path.relative_to(PROJECT_ROOT).as_posix())
    checks.append(
        _check(
            "CSS brace balance",
            not brace_errors,
            "balanced" if not brace_errors else f"unbalanced: {brace_errors}",
        )
    )
    return checks


def _application_checks():
    os.environ.setdefault("CRS_ALLOW_STARTUP_MIGRATIONS", "0")
    from app import app

    app.config.update(TESTING=True)
    checks = []

    template_errors = []
    for path in sorted(TEMPLATE_ROOT.rglob("*.html")):
        template_name = path.relative_to(TEMPLATE_ROOT).as_posix()
        try:
            app.jinja_env.get_template(template_name)
        except Exception as exc:
            template_errors.append(f"{template_name}: {exc}")
    checks.append(
        _check(
            "Jinja template compilation",
            not template_errors,
            f"{len(template_errors)} error(s)",
        )
    )

    literal_paths = set()
    literal_pattern = re.compile(r'(?:href|action)=["\'](/[^"\'{}]*)["\']')
    for path in TEMPLATE_ROOT.rglob("*.html"):
        literal_paths.update(
            match.group(1).split("?", 1)[0]
            for match in literal_pattern.finditer(path.read_text(encoding="utf-8"))
        )
    broken_links = []
    adapter = app.url_map.bind("localhost")
    for path in sorted(literal_paths):
        if path.startswith("/static/"):
            continue
        matched = False
        for method in ("GET", "POST"):
            try:
                adapter.match(path, method=method)
                matched = True
                break
            except MethodNotAllowed:
                continue
            except NotFound:
                break
        if not matched:
            broken_links.append(path)
    checks.append(
        _check(
            "Literal template links",
            not broken_links,
            "all literal links resolve" if not broken_links else f"broken: {broken_links}",
        )
    )

    route_failures = []
    tested_routes = []
    with app.test_client() as client:
        for rule in sorted(app.url_map.iter_rules(), key=lambda row: row.rule):
            if "GET" not in rule.methods or "<" in rule.rule or rule.endpoint == "static":
                continue
            response = client.get(rule.rule, follow_redirects=False)
            tested_routes.append({"path": rule.rule, "status": response.status_code})
            if response.status_code >= 500:
                route_failures.append(f"{rule.rule}: {response.status_code}")

        login_response = client.get("/login")
        csrf_response = client.post(
            "/login",
            data={"username": "release-check", "password": "invalid"},
        )
        missing_response = client.get("/__crs_missing_release_check__")

    checks.extend(
        [
            _check(
                "Unauthenticated GET smoke",
                not route_failures,
                f"{len(tested_routes)} route(s), {len(route_failures)} server error(s)",
            ),
            _check("Login page", login_response.status_code == 200, login_response.status_code),
            _check("CSRF rejection", csrf_response.status_code == 400, csrf_response.status_code),
            _check("Branded 404", missing_response.status_code == 404, missing_response.status_code),
            _check(
                "Security headers",
                all(
                    header in login_response.headers
                    for header in (
                        "Content-Security-Policy",
                        "X-Content-Type-Options",
                        "X-Frame-Options",
                        "Cross-Origin-Opener-Policy",
                        "Cross-Origin-Resource-Policy",
                    )
                ),
                "required browser headers present",
            ),
        ]
    )
    return checks, tested_routes, template_errors, broken_links


def run_validation():
    checks = []
    compile_ok = compileall.compile_dir(
        str(PROJECT_ROOT),
        quiet=1,
        rx=re.compile(r"[\\/](?:venv|\.venv|_local_backups|\.git)[\\/]"),
    )
    checks.append(_check("Python compilation", compile_ok, "compileall"))
    checks.extend(_database_checks())
    checks.extend(_css_checks())
    app_checks, tested_routes, template_errors, broken_links = _application_checks()
    checks.extend(app_checks)
    status = "PASS" if all(row["passed"] for row in checks) else "FAIL"
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "checks": checks,
        "tested_routes": tested_routes,
        "template_errors": template_errors,
        "broken_literal_links": broken_links,
        "plc_calls_performed": False,
        "browser_render_performed": False,
    }


def write_report(report, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "release_validation.json"
    markdown_path = output_dir / "release_validation.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# CRS Release Validation",
        "",
        f"Status: **{report['status']}**",
        f"Generated UTC: `{report['generated_at_utc']}`",
        "",
        "| Check | Result | Detail |",
        "|---|---:|---|",
    ]
    for row in report["checks"]:
        detail = row["detail"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {row['name']} | {'PASS' if row['passed'] else 'FAIL'} | {detail} |"
        )
    lines.extend(
        [
            "",
            f"Unauthenticated GET routes checked: {len(report['tested_routes'])}.",
            "No PLC connection, read, or write was performed.",
            "Browser rendering is tracked separately because local browser access may be policy-blocked.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run safe CRS release validation.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run_validation()
    json_path, markdown_path = write_report(report, args.output_dir)
    print(f"CRS release validation: {report['status']}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
