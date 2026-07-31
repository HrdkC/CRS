"""Build and validate a clean CRS source replacement archive.

The release is allowlist-based. Operational databases, secrets, backups, logs,
Git history, virtual environments and runtime work files cannot enter the ZIP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = "V11.11-RC1"
DEFAULT_OUTPUT = PROJECT_ROOT.parent / f"Centralized_Recipe_System_{VERSION}_Full_Replacement.zip"

ALLOWED_ROOT_FILES = {
    ".env.example",
    ".gitattributes",
    ".gitignore",
    "README.md",
    "app.py",
    "wsgi.py",
    "pytest.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "Create_CRS_Support_Zip.bat",
    "Prepare_CRS_Manual_Zip_Folder.bat",
    "run_crs.bat",
    "setup_crs.bat",
}
ALLOWED_ROOT_DIRS = {
    ".github",
    "config",
    "database",
    "flask_app",
    "helper",
    "plc",
    "plc_tag_import_templates",
    "project_docs",
    "recipe",
    "scripts",
    "tests",
    "tools",
    "utils",
}
FORBIDDEN_PARTS = {
    ".git",
    ".pytest_cache",
    ".vscode",
    "__pycache__",
    "_local_backups",
    "local_backups",
    "study_exports",
    "venv",
    ".venv",
    "instance",
    "logs",
    "reports",
    "recipe_imports",
    "recipe_exports",
}
FORBIDDEN_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".log", ".zip",
    ".bak", ".tmp",
}
FORBIDDEN_NAMES = {
    "database_profile.json",
    "crs_secret_key",
    ".env",
}
TEXT_SUFFIXES = {
    ".py", ".html", ".css", ".js", ".json", ".md", ".txt", ".csv",
    ".yml", ".yaml", ".bat", ".ps1", ".l5x", ".xml", "",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)CRS_SECRET_KEY\s*=\s*['\"]?[A-Za-z0-9+/=_-]{24,}"),
    re.compile(r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"),
)
SECRET_SCAN_EXCLUSIONS = {
    Path("tests/safe/test_database_configuration.py"),
}


def _relative(path: Path) -> Path:
    return path.relative_to(PROJECT_ROOT)


def selected_files() -> list[Path]:
    selected: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = _relative(path)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            continue
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            continue
        if len(rel.parts) == 1:
            if path.name not in ALLOWED_ROOT_FILES:
                continue
        elif rel.parts[0] not in ALLOWED_ROOT_DIRS:
            continue
        if rel.parts[0] == "tests" and not (
            rel.as_posix() == "tests/conftest.py"
            or rel.as_posix().startswith("tests/safe/")
        ):
            continue
        selected.append(path)
    return sorted(selected, key=lambda value: _relative(value).as_posix().lower())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(files: list[Path]) -> list[str]:
    errors: list[str] = []
    if not files:
        return ["No files selected for release."]

    for path in files:
        rel = _relative(path)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            errors.append(f"Forbidden directory selected: {rel}")
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"Forbidden file selected: {rel}")
        if path.suffix.lower() not in TEXT_SUFFIXES or rel in SECRET_SCAN_EXCLUSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"High-confidence secret pattern found: {rel}")
                break

    required = {
        "app.py", "wsgi.py", "README.md", "requirements.txt", "pytest.ini",
        "database/hardening_schema_manager.py",
        "scripts/run_plc_worker.py",
        "scripts/build_clean_release.py",
        "project_docs/current/CURRENT_RELEASE.md",
    }
    selected_names = {_relative(path).as_posix() for path in files}
    for required_name in sorted(required - selected_names):
        errors.append(f"Required release file is missing: {required_name}")
    return errors


def build(output: Path, files: list[Path]) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    release_root = f"Centralized_Recipe_System_{VERSION}"
    manifest = {
        "release": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "files": [
            {
                "path": _relative(path).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            arcname = f"{release_root}/{_relative(path).as_posix()}"
            archive.write(path, arcname)
        archive.writestr(f"{release_root}/RELEASE_MANIFEST.json", manifest_bytes)

    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate/build a clean CRS replacement ZIP.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    files = selected_files()
    errors = validate(files)
    if errors:
        print("Clean release validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    total_size = sum(path.stat().st_size for path in files)
    print(f"Clean release policy: PASS ({len(files)} files, {total_size} bytes)")
    if args.check_only:
        return 0

    output = build(args.output, files)
    print(f"Created: {output}")
    print(f"SHA-256: {sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
