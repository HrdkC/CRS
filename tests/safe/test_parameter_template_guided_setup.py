from pathlib import Path

import pytest

from database.database import get_connection
from database.parameter_template_setup_service import (
    ParameterTemplateSetupError,
    ParameterTemplateSetupService,
)
from scripts.build_css_bundle import OUTPUT_PATH, render_bundle


TABLES = (
    "audit_log",
    "recipe_parameter_values",
    "parameter_definitions",
    "recipes",
    "plc_tags",
)


def _drop_tables():
    conn = get_connection()
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def template_database():
    _drop_tables()
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE plc_tags
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                stage_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                tag_type TEXT,
                is_array INTEGER DEFAULT 0,
                array_size INTEGER,
                array_start_index INTEGER,
                array_end_index INTEGER,
                description TEXT,
                tag_purpose TEXT
            );
            CREATE TABLE parameter_definitions
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                stage_id INTEGER NOT NULL,
                tag_index INTEGER NOT NULL,
                plc_array_index INTEGER,
                parameter_name TEXT NOT NULL,
                parameter_class TEXT,
                unit TEXT,
                min_value REAL,
                max_value REAL,
                default_value REAL,
                datatype TEXT,
                english_memo TEXT,
                used INTEGER DEFAULT 1,
                created_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            );
            CREATE UNIQUE INDEX uq_parameter_tag
                ON parameter_definitions(machine_id, stage_id, tag_index);
            CREATE UNIQUE INDEX uq_parameter_plc_index
                ON parameter_definitions(machine_id, stage_id, plc_array_index);
            CREATE TABLE recipes
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                stage_id INTEGER NOT NULL,
                recipe_code TEXT
            );
            CREATE TABLE recipe_parameter_values
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                parameter_definition_id INTEGER NOT NULL,
                parameter_value REAL,
                is_modified INTEGER DEFAULT 0,
                UNIQUE(recipe_id, parameter_definition_id)
            );
            CREATE TABLE audit_log
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                role TEXT,
                workstation_name TEXT,
                client_ip TEXT,
                plc_name TEXT,
                recipe_code TEXT,
                recipe_version INTEGER,
                record_id INTEGER,
                parameter_name TEXT,
                old_value TEXT,
                new_value TEXT,
                action TEXT,
                change_source TEXT,
                reason TEXT,
                user_agent TEXT,
                forwarded_for TEXT,
                request_host TEXT,
                correlation_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO plc_tags
                (id, machine_id, stage_id, tag_name, tag_type, is_array,
                 array_size, array_start_index, array_end_index, tag_purpose)
            VALUES
                (1, 1, 1, 'CRS_Recipe_Data', 'REAL', 1, 5, 0, 4, 'RECIPE_DATA'),
                (2, 1, 1, 'CRS_Test_Recipe_Data', 'REAL', 1, 5, 0, 4, 'TEST_RECIPE_DATA'),
                (3, 1, 1, 'CRS_Download_Request', 'BOOL', 0, NULL, NULL, NULL, 'DOWNLOAD_REQUEST');
            INSERT INTO recipes(machine_id, stage_id, recipe_code)
            VALUES (1, 1, 'R1'), (1, 1, 'R2');
            """
        )
        conn.commit()
    finally:
        conn.close()
    yield
    _drop_tables()


def test_guided_setup_lists_only_numeric_arrays_and_creates_missing_rows():
    tags = ParameterTemplateSetupService.get_configured_array_tags(1, 1)
    assert [tag["tag_name"] for tag in tags] == [
        "CRS_Recipe_Data",
        "CRS_Test_Recipe_Data",
    ]
    assert tags[0]["recommended"] is True
    assert tags[0]["effective_count"] == 5

    result = ParameterTemplateSetupService.create_missing_from_configured_array(
        machine_id=1,
        stage_id=1,
        source_tag_id=1,
        start_index=0,
        end_index=2,
        name_prefix="P01 FS Parameter",
        unit="MM",
        min_value=0,
        max_value=100,
        default_value=10,
        username="hardik",
        role="ADMIN",
        reason="Create guided parameter rows",
    )
    assert result.created_count == 3
    assert result.skipped_count == 0
    assert result.backfilled_value_count == 6

    second = ParameterTemplateSetupService.create_missing_from_configured_array(
        machine_id=1,
        stage_id=1,
        source_tag_id=1,
        start_index=0,
        end_index=2,
        name_prefix="P01 FS Parameter",
        unit="MM",
        min_value=0,
        max_value=100,
        default_value=10,
        username="hardik",
        role="ADMIN",
        reason="Verify existing rows preserved",
    )
    assert second.created_count == 0
    assert second.skipped_count == 3

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT tag_index, plc_array_index, parameter_name FROM parameter_definitions ORDER BY tag_index"
        ).fetchall()
        values = conn.execute("SELECT COUNT(*) FROM recipe_parameter_values").fetchone()[0]
        audits = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE action='PARAMETER_TEMPLATE_GUIDED_SETUP'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert [tuple(row) for row in rows] == [
        (0, 0, "P01 FS Parameter 000"),
        (1, 1, "P01 FS Parameter 001"),
        (2, 2, "P01 FS Parameter 002"),
    ]
    assert values == 6
    assert audits == 2


def test_guided_setup_rejects_range_outside_configured_array():
    with pytest.raises(ParameterTemplateSetupError, match="inside configured tag range"):
        ParameterTemplateSetupService.create_missing_from_configured_array(
            machine_id=1,
            stage_id=1,
            source_tag_id=1,
            start_index=0,
            end_index=8,
            name_prefix="P01 FS Parameter",
            unit="",
            min_value=0,
            max_value=100,
            default_value=0,
            username="hardik",
            role="ADMIN",
            reason="Reject invalid template range",
        )


def test_bulk_editor_saves_only_submitted_changes_atomically():
    created = ParameterTemplateSetupService.create_missing_from_configured_array(
        machine_id=1,
        stage_id=1,
        source_tag_id=1,
        start_index=0,
        end_index=1,
        name_prefix="P01 FS Parameter",
        unit="",
        min_value=0,
        max_value=100,
        default_value=0,
        username="hardik",
        role="ADMIN",
        reason="Create rows for bulk edit",
    )
    assert created.created_count == 2

    conn = get_connection()
    try:
        ids = [
            row[0]
            for row in conn.execute(
                "SELECT id FROM parameter_definitions ORDER BY tag_index"
            ).fetchall()
        ]
    finally:
        conn.close()

    result = ParameterTemplateSetupService.bulk_update_template(
        machine_id=1,
        stage_id=1,
        changes=[
            {
                "id": ids[0],
                "parameter_name": "Sidewall Length",
                "unit": "MM",
                "min_value": "10",
                "max_value": "500",
                "default_value": "100",
                "used": True,
            },
            {
                "id": ids[1],
                "parameter_name": "Unused Spare",
                "unit": "",
                "min_value": "0",
                "max_value": "1",
                "default_value": "0",
                "used": False,
            },
        ],
        username="hardik",
        role="ADMIN",
        reason="Confirm engineering names and limits",
    )
    assert result.changed_count == 2

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT parameter_name, unit, min_value, max_value, default_value, used "
            "FROM parameter_definitions ORDER BY tag_index"
        ).fetchall()
        row_audits = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE action='PARAMETER_TEMPLATE_ROW_UPDATED'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert tuple(rows[0]) == ("Sidewall Length", "MM", 10.0, 500.0, 100.0, 1)
    assert tuple(rows[1]) == ("Unused Spare", "", 0.0, 1.0, 0.0, 0)
    assert row_audits == 2


def test_guided_template_assets_and_configuration_label_are_present():
    root = Path(__file__).resolve().parents[2]
    template = (root / "flask_app/templates/parameters/parameters.html").read_text(encoding="utf-8")
    route = (root / "flask_app/routes/parameter_routes.py").read_text(encoding="utf-8")
    readiness = (root / "flask_app/templates/configuration/stage_readiness.html").read_text(encoding="utf-8")
    main_css = (root / "flask_app/static/css/main.css").read_text(encoding="utf-8")
    js = (root / "flask_app/static/js/pages/parameter-template-setup.js").read_text(encoding="utf-8")

    assert 'name="source_tag_id"' in template
    assert "Create Missing Template Rows" in template
    assert "Save Changed Rows" in template
    assert "/parameters/template-setup/<machine_code>/<stage_code>" in route
    assert "/parameters/bulk-update/<machine_code>/<stage_code>" in route
    assert "Guided Setup" in readiness
    assert "35_parameter_template_guided_setup.css" in main_css
    assert "changes_json" in route
    assert "rowSnapshot" in js
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_bundle()
