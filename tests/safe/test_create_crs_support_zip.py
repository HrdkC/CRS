import sqlite3
import zipfile
from pathlib import Path

from scripts.create_crs_support_zip import (
    build_support_zip,
    prepare_manual_zip_folder,
)


def test_support_zip_uses_online_database_backup_and_excludes_runtime_files(tmp_path):
    project = tmp_path / "Centralized_Recipe_System"
    database_dir = project / "database"
    database_dir.mkdir(parents=True)
    (project / "app.py").write_text("print('CRS')\n", encoding="utf-8")
    (project / "logs").mkdir()
    (project / "logs" / "crs.log").write_text("private runtime log")
    (project / "instance").mkdir()
    (project / "instance" / "crs_secret_key").write_text("not-for-support")
    (project / "venv").mkdir()
    (project / "venv" / "ignored.txt").write_text("ignored")
    (project / "old.zip").write_bytes(b"ignored")

    database = database_dir / "recipe.db"
    writer = sqlite3.connect(database)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute(
            "CREATE TABLE recipes (id INTEGER PRIMARY KEY, recipe_code TEXT)"
        )
        writer.execute(
            "INSERT INTO recipes (recipe_code) VALUES (?)",
            ("P01_FS_TEST",),
        )
        writer.commit()
        assert database.with_name("recipe.db-wal").exists()

        output = tmp_path / "CRS_Current_Support.zip"
        result = build_support_zip(project, database, output)
    finally:
        writer.close()

    assert result["database"]["integrity_check"] == "ok"
    assert result["database"]["foreign_key_violations"] == 0

    extract_root = tmp_path / "extracted"
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        archive.extractall(extract_root)

    assert any(name.endswith("/database/recipe.db") for name in names)
    assert not any(name.endswith("recipe.db-wal") for name in names)
    assert not any(name.endswith("recipe.db-shm") for name in names)
    assert not any("crs_secret_key" in name for name in names)
    assert not any("/logs/" in name for name in names)
    assert not any("/venv/" in name for name in names)
    assert not any(name.endswith("/old.zip") for name in names)

    snapshot = next(extract_root.rglob("database/recipe.db"))
    connection = sqlite3.connect(snapshot)
    try:
        recipe_code = connection.execute(
            "SELECT recipe_code FROM recipes"
        ).fetchone()[0]
    finally:
        connection.close()
    assert recipe_code == "P01_FS_TEST"


def test_support_zip_must_be_written_outside_project(tmp_path):
    project = tmp_path / "Centralized_Recipe_System"
    database_dir = project / "database"
    database_dir.mkdir(parents=True)
    database = database_dir / "recipe.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")

    try:
        build_support_zip(project, database, project / "unsafe.zip")
    except ValueError as error:
        assert "outside the CRS project folder" in str(error)
    else:
        raise AssertionError("Expected an unsafe output-path failure.")


def test_manual_zip_folder_is_unlocked_complete_and_excludes_sidecars(tmp_path):
    project = tmp_path / "Centralized_Recipe_System"
    database_dir = project / "database"
    database_dir.mkdir(parents=True)
    (project / "app.py").write_text("print('CRS')\n", encoding="utf-8")
    (project / "instance").mkdir()
    (project / "instance" / "crs_secret_key").write_text("excluded")

    database = database_dir / "recipe.db"
    writer = sqlite3.connect(database)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute(
            "CREATE TABLE recipes (id INTEGER PRIMARY KEY, recipe_code TEXT)"
        )
        writer.execute(
            "INSERT INTO recipes (recipe_code) VALUES (?)",
            ("P01_SS_TEST",),
        )
        writer.commit()

        prepared = tmp_path / "CRS_Manual_Zip_Ready"
        result = prepare_manual_zip_folder(project, database, prepared)
    finally:
        writer.close()

    assert result["database"]["integrity_check"] == "ok"
    assert (prepared / "app.py").is_file()
    assert (prepared / "database" / "recipe.db").is_file()
    assert not (prepared / "database" / "recipe.db-wal").exists()
    assert not (prepared / "database" / "recipe.db-shm").exists()
    assert not (prepared / "instance" / "crs_secret_key").exists()

    snapshot = sqlite3.connect(prepared / "database" / "recipe.db")
    try:
        assert snapshot.execute(
            "SELECT recipe_code FROM recipes"
        ).fetchone()[0] == "P01_SS_TEST"
    finally:
        snapshot.close()

    renamed = prepared.with_name("CRS_Manual_Zip_Renamed")
    prepared.replace(renamed)
    assert renamed.is_dir()
