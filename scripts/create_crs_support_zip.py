"""Create a shareable CRS support ZIP while the application is running.

The operational SQLite database is copied with SQLite's online backup API.
Transient WAL/SHM files, secrets, logs, virtual environments, caches, Git data,
existing archives and local backups are never included.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "database" / "recipe.db"

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "_local_backups",
    "instance",
    "local_backups",
    "logs",
    "recipe_exports",
    "recipe_imports",
    "reports",
    "study_exports",
    "venv",
}
EXCLUDED_FILE_NAMES = {
    ".env",
    "crs_secret_key",
    "database_profile.json",
    "plc_worker_status.json",
}
EXCLUDED_SUFFIXES = {
    ".bak",
    ".db",
    ".db-journal",
    ".db-shm",
    ".db-wal",
    ".journal",
    ".log",
    ".pyc",
    ".pyo",
    ".shm",
    ".sqlite",
    ".sqlite3",
    ".tmp",
    ".wal",
    ".zip",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_excluded(relative_path: Path) -> bool:
    if any(
        part in EXCLUDED_DIRECTORY_NAMES or part.startswith(".codex_test_")
        for part in relative_path.parts[:-1]
    ):
        return True
    if relative_path.name in EXCLUDED_FILE_NAMES:
        return True
    return any(
        relative_path.name.lower().endswith(suffix)
        for suffix in EXCLUDED_SUFFIXES
    )


def _copy_source_tree(project_root: Path, staging_root: Path) -> int:
    copied = 0
    for source in sorted(project_root.rglob("*")):
        if not source.is_file() or source.is_symlink():
            continue
        relative = source.relative_to(project_root)
        if _is_excluded(relative):
            continue
        destination = staging_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return copied


def _backup_sqlite(source_path: Path, destination_path: Path) -> dict:
    if not source_path.is_file():
        raise FileNotFoundError(f"Operational database not found: {source_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source_uri = source_path.resolve().as_uri() + "?mode=ro"
    with closing(
        sqlite3.connect(source_uri, uri=True, timeout=30)
    ) as source:
        with closing(
            sqlite3.connect(destination_path, timeout=30)
        ) as destination:
            source.backup(destination, pages=256, sleep=0.05)
            integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = destination.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

    if integrity.lower() != "ok":
        raise RuntimeError(f"SQLite backup integrity check failed: {integrity}")
    if foreign_keys:
        raise RuntimeError(
            f"SQLite backup has {len(foreign_keys)} foreign-key violation(s)."
        )

    return {
        "integrity_check": integrity,
        "foreign_key_violations": 0,
        "size": destination_path.stat().st_size,
        "sha256": _sha256(destination_path),
    }


def _write_manifest(
    staging_root: Path,
    database_evidence: dict,
    generated_at: datetime,
    snapshot_type: str = "CRS_SUPPORT_SNAPSHOT",
) -> Path:
    files = []
    for path in sorted(staging_root.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(staging_root).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )

    manifest = {
        "archive_type": snapshot_type,
        "generated_at_utc": generated_at.isoformat(),
        "database": database_evidence,
        "file_count_before_manifest": len(files),
        "files": files,
        "excluded": {
            "live_database_sidecars": True,
            "secrets": True,
            "logs": True,
            "virtual_environments": True,
            "git_history": True,
            "existing_archives": True,
        },
    }
    path = staging_root / "SUPPORT_SNAPSHOT_MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def prepare_manual_zip_folder(
    project_root: Path,
    database_path: Path,
    output_folder: Path,
) -> dict:
    project_root = project_root.resolve()
    database_path = database_path.resolve()
    output_folder = output_folder.resolve()
    generated_at = datetime.now(timezone.utc)

    if output_folder.is_relative_to(project_root):
        raise ValueError(
            "Manual ZIP folder must be outside the live CRS project folder."
        )
    if output_folder.exists():
        raise FileExistsError(
            f"Manual ZIP folder already exists: {output_folder}"
        )

    temporary_folder = output_folder.with_name(
        output_folder.name + ".preparing"
    )
    if temporary_folder.exists():
        shutil.rmtree(temporary_folder)

    try:
        temporary_folder.mkdir(parents=True)
        source_file_count = _copy_source_tree(project_root, temporary_folder)
        database_evidence = _backup_sqlite(
            database_path,
            temporary_folder / "database" / "recipe.db",
        )
        _write_manifest(
            temporary_folder,
            database_evidence,
            generated_at,
            snapshot_type="CRS_MANUAL_ZIP_READY_FOLDER",
        )
        temporary_folder.replace(output_folder)
    except Exception:
        if temporary_folder.exists():
            shutil.rmtree(temporary_folder, ignore_errors=True)
        raise

    return {
        "output": str(output_folder),
        "source_file_count": source_file_count,
        "database": database_evidence,
    }


def build_support_zip(
    project_root: Path,
    database_path: Path,
    output_path: Path,
) -> dict:
    project_root = project_root.resolve()
    database_path = database_path.resolve()
    output_path = output_path.resolve()
    generated_at = datetime.now(timezone.utc)

    if output_path.is_relative_to(project_root):
        raise ValueError("Support ZIP output must be outside the CRS project folder.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="crs_support_snapshot_",
        dir=output_path.parent,
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        archive_root_name = (
            "Centralized_Recipe_System_Support_"
            + generated_at.strftime("%Y%m%d_%H%M%S")
        )
        staging_root = temporary_root / archive_root_name
        staging_root.mkdir()

        source_file_count = _copy_source_tree(project_root, staging_root)
        database_evidence = _backup_sqlite(
            database_path,
            staging_root / "database" / "recipe.db",
        )
        _write_manifest(staging_root, database_evidence, generated_at)

        with zipfile.ZipFile(
            output_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in sorted(staging_root.rglob("*")):
                if path.is_file():
                    archive.write(
                        path,
                        (Path(archive_root_name) / path.relative_to(staging_root)),
                    )

    return {
        "output": str(output_path),
        "source_file_count": source_file_count,
        "database": database_evidence,
        "zip_size": output_path.stat().st_size,
        "zip_sha256": _sha256(output_path),
    }


def main(argv=None) -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(
        description="Create a live, shareable CRS support ZIP."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--folder-only",
        action="store_true",
        help="Prepare an unlocked folder for manual Windows ZIP creation.",
    )
    args = parser.parse_args(argv)

    if args.folder_only:
        output = args.output or (
            PROJECT_ROOT.parent / f"CRS_Manual_Zip_Ready_{timestamp}"
        )
        result = prepare_manual_zip_folder(
            args.project_root,
            args.database,
            output,
        )
        print("CRS manual ZIP folder: READY")
        print(f"Folder             : {result['output']}")
        print(f"Source files       : {result['source_file_count']}")
        print(f"Database integrity : {result['database']['integrity_check']}")
        print(
            "Foreign key issues : "
            f"{result['database']['foreign_key_violations']}"
        )
        print("Right-click this folder and select Compress to ZIP.")
        return 0

    output = args.output or (
        PROJECT_ROOT.parent / f"CRS_Current_Support_{timestamp}.zip"
    )
    result = build_support_zip(
        args.project_root,
        args.database,
        output,
    )
    print("CRS support ZIP: SUCCESS")
    print(f"Output             : {result['output']}")
    print(f"Source files       : {result['source_file_count']}")
    print(f"Database integrity : {result['database']['integrity_check']}")
    print(
        "Foreign key issues : "
        f"{result['database']['foreign_key_violations']}"
    )
    print(f"ZIP size           : {result['zip_size']}")
    print(f"ZIP SHA-256        : {result['zip_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
