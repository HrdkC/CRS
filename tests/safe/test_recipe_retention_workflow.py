from database import database as database_module
from database.hardening_schema_manager import apply_v11_11_hardening_schema
from database.recipe_manager import RecipeManager
from database.recipe_retention_manager import RecipeRetentionManager


def _create_schema_and_data():
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
                created_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_test_only INTEGER DEFAULT 0
            );
            CREATE TABLE recipe_parameter_values
            (
                id INTEGER PRIMARY KEY,
                recipe_id INTEGER,
                parameter_definition_id INTEGER,
                parameter_value REAL,
                is_modified INTEGER DEFAULT 0
            );
            CREATE TABLE recipe_phase_control
            (
                id INTEGER PRIMARY KEY,
                recipe_id INTEGER,
                line_no INTEGER,
                phase_control_id INTEGER,
                stop_option TEXT,
                position_option TEXT,
                sequence_no INTEGER,
                used INTEGER DEFAULT 1
            );
            CREATE TABLE recipe_status_history
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER,
                recipe_code TEXT,
                old_status TEXT,
                new_status TEXT,
                changed_by TEXT,
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                remarks TEXT
            );
            CREATE TABLE recipe_download_history
            (
                id INTEGER PRIMARY KEY,
                recipe_code TEXT,
                recipe_version INTEGER
            );
            CREATE TABLE recipe_upload_history
            (
                id INTEGER PRIMARY KEY,
                recipe_code TEXT,
                recipe_version INTEGER
            );
            CREATE TABLE recipe_versions
            (
                id INTEGER PRIMARY KEY,
                recipe_code TEXT,
                version INTEGER,
                recipe_id INTEGER
            );
            CREATE TABLE recipe_version_values
            (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER,
                parameter_definition_id INTEGER,
                parameter_value REAL
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
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE audit_log
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
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
                request_host TEXT
            );

            INSERT INTO users VALUES (1, 'hardik', 'ADMIN', 1);
            INSERT INTO tbm_machines VALUES (1, 'P01');
            INSERT INTO machine_stages VALUES (1, 1, 'FIRST_STAGE');

            INSERT INTO recipes
            (id, machine_id, stage_id, recipe_code, recipe_name, version,
             status, created_by, is_test_only)
            VALUES
            (1, 1, 1, 'GT_TEST', 'GT Test', 1, 'DRAFT', 'hardik', 1),
            (2, 1, 1, 'PROD_01', 'Production', 1, 'RELEASED', 'hardik', 0);

            INSERT INTO recipe_parameter_values VALUES (1, 1, 10, 12.5, 0);
            INSERT INTO recipe_phase_control VALUES (1, 1, 1, 20, 'No', 'No', 1, 1);
            INSERT INTO recipe_status_history
            (recipe_id, recipe_code, old_status, new_status, changed_by, remarks)
            VALUES
            (1, 'GT_TEST', '', 'DRAFT', 'hardik', 'Created'),
            (2, 'PROD_01', 'APPROVED', 'RELEASED', 'hardik', 'Released');
            """
        )
        conn.commit()
    finally:
        conn.close()
    apply_v11_11_hardening_schema()


def test_archive_hides_recipe_and_restore_returns_it(tmp_path, monkeypatch):
    database_path = tmp_path / "retention_archive_restore.db"
    monkeypatch.setattr(database_module, "DATABASE_PATH", database_path)
    _create_schema_and_data()

    policy = RecipeRetentionManager.get_policy(1)
    assert policy["can_archive"] is True

    RecipeRetentionManager.archive_recipe(
        recipe_id=1,
        actor="hardik",
        actor_role="ADMIN",
        reason="Obsolete trial recipe",
        confirmation_code="GT_TEST",
    )

    assert RecipeManager.get_recipe_by_id(1) is None
    assert [r["recipe_code"] for r in RecipeManager.get_recipes(1, 1)] == ["PROD_01"]
    archived = RecipeRetentionManager.list_archived(1, 1)
    assert len(archived) == 1
    assert archived[0]["recipe_code"] == "GT_TEST"
    assert archived[0]["can_permanently_delete"] is True

    RecipeRetentionManager.restore_recipe(
        recipe_id=1,
        actor="hardik",
        actor_role="ADMIN",
        reason="Trial recipe needed again",
        confirmation_code="GT_TEST",
    )

    assert RecipeManager.get_recipe_by_id(1)["recipe_code"] == "GT_TEST"
    assert RecipeRetentionManager.list_archived(1, 1) == []

    conn = database_module.get_connection()
    try:
        events = [
            row[0]
            for row in conn.execute(
                "SELECT event_type FROM recipe_retention_history ORDER BY id"
            ).fetchall()
        ]
        actions = [
            row[0]
            for row in conn.execute(
                "SELECT action FROM audit_log WHERE action LIKE 'RECIPE_%' ORDER BY id"
            ).fetchall()
        ]
    finally:
        conn.close()

    assert events == ["ARCHIVED", "RESTORED"]
    assert actions == ["RECIPE_ARCHIVED", "RECIPE_ARCHIVE_RESTORED"]


def test_permanent_delete_only_removes_eligible_archived_test_draft(tmp_path, monkeypatch):
    database_path = tmp_path / "retention_delete.db"
    monkeypatch.setattr(database_module, "DATABASE_PATH", database_path)
    _create_schema_and_data()

    RecipeRetentionManager.archive_recipe(
        recipe_id=1,
        actor="hardik",
        actor_role="ADMIN",
        reason="Trial recipe is no longer required",
        confirmation_code="GT_TEST",
    )
    result = RecipeRetentionManager.permanently_delete_recipe(
        recipe_id=1,
        actor="hardik",
        actor_role="ADMIN",
        reason="Approved removal of unused trial recipe",
        confirmation_code="GT_TEST",
        delete_confirmation="DELETE",
    )

    assert result["recipe_code"] == "GT_TEST"

    conn = database_module.get_connection()
    try:
        assert conn.execute("SELECT COUNT(*) FROM recipes WHERE id=1").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM recipe_parameter_values WHERE recipe_id=1").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM recipe_phase_control WHERE recipe_id=1").fetchone()[0] == 0
        tombstone = conn.execute(
            """
            SELECT event_type, recipe_code, metadata_json
            FROM recipe_retention_history
            WHERE event_type='PERMANENTLY_DELETED'
            """
        ).fetchone()
        audit = conn.execute(
            "SELECT action FROM audit_log WHERE action='RECIPE_PERMANENTLY_DELETED'"
        ).fetchone()
    finally:
        conn.close()

    assert tombstone["recipe_code"] == "GT_TEST"
    assert tombstone["event_type"] == "PERMANENTLY_DELETED"
    assert audit["action"] == "RECIPE_PERMANENTLY_DELETED"


def test_released_recipe_is_protected_from_archive_and_delete(tmp_path, monkeypatch):
    database_path = tmp_path / "retention_protected.db"
    monkeypatch.setattr(database_module, "DATABASE_PATH", database_path)
    _create_schema_and_data()

    policy = RecipeRetentionManager.get_policy(2)
    assert policy["can_archive"] is False
    assert any("Released" in blocker for blocker in policy["archive_blockers"])
    assert policy["can_permanently_delete"] is False
