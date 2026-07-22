from database import database as database_module
from database.hardening_schema_manager import apply_v11_11_hardening_schema
from database.recipe_parameter_value_manager import RecipeParameterValueManager


def _create_recipe_audit_tables():
    conn = database_module.get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE users
            (
                id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT,
                active INTEGER DEFAULT 1
            );
            CREATE TABLE tbm_machines
            (
                id INTEGER PRIMARY KEY,
                machine_code TEXT
            );
            CREATE TABLE machine_stages
            (
                id INTEGER PRIMARY KEY,
                machine_id INTEGER,
                stage_type TEXT
            );
            CREATE TABLE recipes
            (
                id INTEGER PRIMARY KEY,
                machine_id INTEGER,
                stage_id INTEGER,
                recipe_code TEXT,
                recipe_name TEXT,
                version INTEGER DEFAULT 1,
                status TEXT,
                created_by TEXT
            );
            CREATE TABLE parameter_definitions
            (
                id INTEGER PRIMARY KEY,
                machine_id INTEGER,
                stage_id INTEGER,
                parameter_name TEXT,
                tag_index INTEGER,
                min_value REAL,
                max_value REAL
            );
            CREATE TABLE recipe_parameter_values
            (
                id INTEGER PRIMARY KEY,
                recipe_id INTEGER,
                parameter_definition_id INTEGER,
                parameter_value REAL,
                is_modified INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE recipe_parameter_audit
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER,
                recipe_parameter_value_id INTEGER,
                parameter_definition_id INTEGER,
                old_value REAL,
                new_value REAL,
                changed_by TEXT,
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                recipe_code TEXT,
                recipe_version INTEGER,
                parameter_name TEXT,
                tag_index INTEGER,
                change_source TEXT,
                change_reason TEXT,
                user_role TEXT,
                client_ip TEXT,
                workstation_name TEXT
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
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO users VALUES (1, 'engineer', 'ENGINEERING', 1);
            INSERT INTO tbm_machines VALUES (1, 'P01');
            INSERT INTO machine_stages VALUES (1, 1, 'FIRST_STAGE');
            INSERT INTO recipes VALUES (1, 1, 1, 'TEST_P01FS', 'Test P01 FS', 1, 'RELEASED', 'engineer');
            INSERT INTO parameter_definitions VALUES (1, 1, 1, 'WIDTH', 1, 0, 100);
            INSERT INTO recipe_parameter_values VALUES (1, 1, 1, 10, 0, CURRENT_TIMESTAMP);
            """
        )
        conn.commit()
    finally:
        conn.close()
    apply_v11_11_hardening_schema()


def test_recipe_parameter_value_update_commits_value_and_both_audits(tmp_path, monkeypatch):
    database_path = tmp_path / "recipe_edit_success.db"
    monkeypatch.setattr(database_module, "DATABASE_PATH", database_path)

    _create_recipe_audit_tables()

    result = RecipeParameterValueManager.update_recipe_value(
        value_id=1,
        new_value=25,
        changed_by="engineer",
        change_reason="Verified recipe value correction",
        user_role="ENGINEERING",
        change_source="SAFE_TEST",
        client_ip="127.0.0.1",
        workstation_name="SAFE-TEST",
    )

    assert result["success"] is True
    assert result["changed"] is True
    assert result["old_value"] == 10
    assert result["new_value"] == 25

    conn = database_module.get_connection()
    try:
        value = conn.execute(
            "SELECT parameter_value, is_modified FROM recipe_parameter_values WHERE id=1"
        ).fetchone()
        parameter_audit_count = conn.execute(
            "SELECT COUNT(*) FROM recipe_parameter_audit WHERE recipe_parameter_value_id=1"
        ).fetchone()[0]
        general_audit_count = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE action='RECIPE_PARAMETER_CHANGED'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert value["parameter_value"] == 25
    assert value["is_modified"] == 1
    assert parameter_audit_count == 1
    assert general_audit_count == 1
