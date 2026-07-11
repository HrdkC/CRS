"""Generate a read-only CRS repository and route inventory.

This command deliberately avoids importing the Flask application because app
creation performs schema synchronization. It is safe to run during release
review and workstation recovery validation.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "audit"
ROUTE_ROOT = PROJECT_ROOT / "flask_app" / "routes"
APP_ENTRY = PROJECT_ROOT / "app.py"
TEMPLATE_ROOT = PROJECT_ROOT / "flask_app" / "templates"
STATIC_ROOT = PROJECT_ROOT / "flask_app" / "static"
DATABASE_PATH = PROJECT_ROOT / "database" / "recipe.db"

AUTH_MARKERS = (
    'session.get("logged_in")',
    "session.get('logged_in')",
    "role_can(",
    "is_admin_role(",
    "_is_admin(",
    "_can_",
)
MUTATING_NAME_MARKERS = (
    "create",
    "update",
    "save",
    "delete",
    "disable",
    "enable",
    "remove",
    "import",
    "confirm",
    "release",
    "approve",
    "reject",
    "restore",
    "download",
    "upload",
    "logout",
    "reset",
    "change",
    "map",
)


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _literal(value):
    try:
        return ast.literal_eval(value)
    except (ValueError, TypeError):
        return None


def _route_inventory():
    routes = []
    parse_errors = []

    app_tree = ast.parse(
        APP_ENTRY.read_text(encoding="utf-8"),
        filename=str(APP_ENTRY),
    )
    active_route_modules = {
        node.module.rsplit(".", 1)[-1]
        for node in app_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("flask_app.routes.")
    }

    for path in sorted(ROUTE_ROOT.glob("*.py")):
        if path.stem not in active_route_modules:
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            parse_errors.append(
                {"file": _relative(path), "error": str(exc)}
            )
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if not (
                    isinstance(func, ast.Attribute)
                    and func.attr == "route"
                ):
                    continue

                route_path = _literal(decorator.args[0]) if decorator.args else None
                methods = ["GET"]
                for keyword in decorator.keywords:
                    if keyword.arg == "methods":
                        methods = _literal(keyword.value) or ["GET"]
                methods = sorted(str(method).upper() for method in methods)
                function_source = ast.get_source_segment(source, node) or ""
                auth_markers = [
                    marker for marker in AUTH_MARKERS if marker in function_source
                ]
                auth_helper_calls = []
                for child in ast.walk(node):
                    if not isinstance(child, ast.Call):
                        continue
                    if not isinstance(child.func, ast.Name):
                        continue
                    helper_name = child.func.id.lower()
                    if helper_name.startswith("_") and any(
                        marker in helper_name
                        for marker in ("allowed", "required", "authorized")
                    ):
                        auth_helper_calls.append(child.func.id)
                auth_markers.extend(sorted(set(auth_helper_calls)))
                mutating_name = any(
                    marker in node.name.lower()
                    for marker in MUTATING_NAME_MARKERS
                )
                state_methods = sorted(
                    set(methods).intersection({"POST", "PUT", "PATCH", "DELETE"})
                )
                routes.append(
                    {
                        "path": route_path or "<dynamic>",
                        "methods": methods,
                        "endpoint_function": node.name,
                        "file": _relative(path),
                        "line": node.lineno,
                        "auth_markers": auth_markers,
                        "has_auth_indicator": bool(auth_markers),
                        "state_changing_methods": state_methods,
                        "possible_state_change_on_get": bool(
                            mutating_name and methods == ["GET"]
                        ),
                    }
                )

    return routes, parse_errors


def _database_inventory():
    if not DATABASE_PATH.exists():
        return {"exists": False, "path": _relative(DATABASE_PATH)}

    uri = f"file:{DATABASE_PATH.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
        ]
        indexes = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
        ]
        columns = {
            table: [
                {
                    "name": row[1],
                    "type": row[2],
                    "not_null": bool(row[3]),
                    "primary_key": bool(row[5]),
                }
                for row in connection.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
            ]
            for table in tables
        }
        return {
            "exists": True,
            "path": _relative(DATABASE_PATH),
            "tables": tables,
            "indexes": indexes,
            "columns": columns,
        }
    finally:
        connection.close()


def _file_inventory():
    ignored_parts = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "_local_backups",
    }
    files = [
        path
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file() and not ignored_parts.intersection(path.parts)
    ]
    by_suffix = {}
    for path in files:
        suffix = path.suffix.lower() or "<none>"
        by_suffix[suffix] = by_suffix.get(suffix, 0) + 1

    database_artifacts = [
        _relative(path)
        for path in files
        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
        and path != DATABASE_PATH
    ]
    debug_artifacts = [
        _relative(path)
        for path in files
        if re.search(r"(^|[/\\])(debug|dump|temp|tmp)", str(path), re.I)
    ]

    return {
        "total_files": len(files),
        "by_suffix": dict(sorted(by_suffix.items())),
        "templates": sorted(_relative(path) for path in TEMPLATE_ROOT.rglob("*.html")),
        "stylesheets": sorted(_relative(path) for path in STATIC_ROOT.rglob("*.css")),
        "scripts": sorted(_relative(path) for path in STATIC_ROOT.rglob("*.js")),
        "tests": sorted(_relative(path) for path in (PROJECT_ROOT / "tests").rglob("*.py")),
        "extra_database_artifacts": sorted(database_artifacts),
        "possible_debug_artifacts": sorted(debug_artifacts),
    }


def build_report():
    routes, parse_errors = _route_inventory()
    unauthenticated_state_routes = [
        route
        for route in routes
        if route["state_changing_methods"] and not route["has_auth_indicator"]
    ]
    possible_get_mutations = [
        route for route in routes if route["possible_state_change_on_get"]
    ]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "summary": {
            "route_count": len(routes),
            "route_parse_errors": len(parse_errors),
            "state_routes_without_local_auth_indicator": len(
                unauthenticated_state_routes
            ),
            "possible_state_change_get_routes": len(possible_get_mutations),
        },
        "routes": routes,
        "route_parse_errors": parse_errors,
        "review_queues": {
            "state_routes_without_local_auth_indicator": unauthenticated_state_routes,
            "possible_state_change_get_routes": possible_get_mutations,
        },
        "database": _database_inventory(),
        "files": _file_inventory(),
    }


def write_report(report, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "repository_audit.json"
    markdown_path = output_dir / "repository_audit.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    summary = report["summary"]
    files = report["files"]
    database = report["database"]
    markdown_path.write_text(
        "\n".join(
            [
                "# CRS Repository Audit",
                "",
                f"Generated UTC: `{report['generated_at_utc']}`",
                "",
                "## Inventory",
                "",
                f"- Repository files: {files['total_files']}",
                f"- Flask route declarations: {summary['route_count']}",
                f"- Templates: {len(files['templates'])}",
                f"- CSS files: {len(files['stylesheets'])}",
                f"- JavaScript files: {len(files['scripts'])}",
                f"- Test scripts: {len(files['tests'])}",
                f"- Database tables: {len(database.get('tables', []))}",
                f"- Database indexes: {len(database.get('indexes', []))}",
                "",
                "## Manual Review Queues",
                "",
                "Static indicators are review aids, not proof of a vulnerability.",
                "",
                "- State-changing routes without a local auth indicator: "
                f"{summary['state_routes_without_local_auth_indicator']}",
                "- Possible state-changing GET routes: "
                f"{summary['possible_state_change_get_routes']}",
                f"- Extra database artifacts: {len(files['extra_database_artifacts'])}",
                f"- Route parse errors: {summary['route_parse_errors']}",
                "",
                "See `repository_audit.json` for file, route, line, method, "
                "schema, and review-queue details.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return json_path, markdown_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a read-only CRS repository audit."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="report directory (default: reports/audit)",
    )
    args = parser.parse_args(argv)
    json_path, markdown_path = write_report(
        build_report(),
        args.output_dir,
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
