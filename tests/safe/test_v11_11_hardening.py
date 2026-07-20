from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from database.database import get_connection
from database.hardening_schema_manager import apply_v11_11_hardening_schema
from database.plc_crs_test_tag_definitions import (
    get_tag_definitions,
    payload_size_for_stage,
)
from database.recipe_parameter_audit_manager import RecipeParameterAuditManager
from database.recipe_parameter_value_manager import RecipeParameterValueManager
from database.recipe_resource_lock_manager import RecipeResourceLockManager
from database.stage_plc_tag_requirement_manager import StagePLCTagRequirementManager
from database.user_session_manager import ActiveSessionConflict, UserSessionManager
from flask_app.security import login_throttle


def _drop_runtime_tables():
    conn = get_connection()
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in (
            "recipe_resource_claims",
            "recipe_resource_locks",
            "login_throttle",
            "schema_version",
            "recipe_phase_control_audit",
            "recipe_parameter_audit",
            "audit_log",
            "recipe_parameter_values",
            "parameter_definitions",
            "recipes",
            "machine_stages",
            "tbm_machines",
            "user_sessions",
            "users",
        ):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def clean_hardening_database():
    _drop_runtime_tables()
    yield
    _drop_runtime_tables()


def test_stage_payload_sizes_are_not_global():
    assert payload_size_for_stage("FS") == 500
    assert payload_size_for_stage("SECOND_STAGE") == 150

    fs = {item["purpose"]: item for item in get_tag_definitions(stage_type="FS")}
    ss = {item["purpose"]: item for item in get_tag_definitions(stage_type="SS")}
    assert fs["RECIPE_DATA"]["array_size"] == 500
    assert fs["TEST_RECIPE_DATA"]["array_end_index"] == 499
    assert ss["RECIPE_DATA"]["array_size"] == 150
    assert ss["TEST_RECIPE_DATA"]["array_end_index"] == 149


def test_second_stage_phase_contract_is_selection_only():
    assert StagePLCTagRequirementManager.stage_phase_purposes("SECOND_STAGE") == {
        "CAP_STRIP_PHASE_CONTROL_STRING",
        "BT_PHASE_CONTROL_STRING",
    }
    for legacy_purpose in (
        "CAP_STRIP_PHASE_STOP_STRING",
        "BT_PHASE_STOP_STRING",
        "BT_PHASE_POSITION_STRING",
    ):
        assert not StagePLCTagRequirementManager.is_purpose_allowed_for_stage(
            legacy_purpose, "SECOND_STAGE"
        )
    template = Path(
        "flask_app/templates/recipes/recipe_phase_control.html"
    ).read_text(encoding="utf-8")
    assert 'type="hidden" name="stop_option_' not in template
    assert 'type="hidden" name="position_option_' not in template
    download_template = Path(
        "flask_app/templates/recipes/download_preparation.html"
    ).read_text(encoding="utf-8")
    assert '{% set phase_purposes = ["CAP_STRIP_PHASE_CONTROL_STRING", "BT_PHASE_CONTROL_STRING"] %}' in download_template


def test_atomic_resource_claim_has_exactly_one_winner():
    apply_v11_11_hardening_schema()

    def claim(session_id):
        return RecipeResourceLockManager.acquire_lock(
            resource_type="RECIPE_EDIT",
            resource_id=101,
            operation_type="PARAMETER_EDIT",
            username=f"user-{session_id}",
            user_role="ENGINEERING",
            session_id=session_id,
            ttl_minutes=5,
        )["acquired"]

    with ThreadPoolExecutor(max_workers=20) as pool:
        outcomes = list(pool.map(claim, range(1, 41)))

    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 39


def _create_session_tables():
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE users
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                role TEXT,
                active INTEGER DEFAULT 1,
                password_reset_required INTEGER DEFAULT 0
            );
            CREATE TABLE user_sessions
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                role TEXT,
                client_ip TEXT,
                workstation_name TEXT,
                user_agent TEXT,
                forwarded_for TEXT,
                request_host TEXT,
                login_source TEXT,
                replaced_existing_sessions INTEGER DEFAULT 0,
                login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME,
                heartbeat_at DATETIME,
                logout_time DATETIME,
                logout_reason TEXT,
                auto_logged_out INTEGER DEFAULT 0
            );
            INSERT INTO users(username, role, active) VALUES ('atomic-user', 'ENGINEERING', 1);
            """
        )
        conn.commit()
    finally:
        conn.close()
    apply_v11_11_hardening_schema()


def test_atomic_single_session_allows_one_login():
    _create_session_tables()

    def login(attempt):
        try:
            session_id, _ = UserSessionManager.login(
                username="atomic-user",
                role="ENGINEERING",
                client_ip=f"127.0.0.{attempt + 1}",
                workstation_name=f"WS-{attempt}",
            )
            return ("created", session_id)
        except ActiveSessionConflict:
            return ("blocked", None)

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(login, range(12)))

    assert sum(result[0] == "created" for result in results) == 1
    assert sum(result[0] == "blocked" for result in results) == 11


def test_login_throttle_is_database_backed(monkeypatch):
    apply_v11_11_hardening_schema()
    monkeypatch.setattr(login_throttle, "MAX_FAILURES", 3)
    monkeypatch.setattr(login_throttle, "LOCKOUT_SECONDS", 120)
    for _ in range(3):
        login_throttle.record_login_failure("ExampleUser", "10.10.10.10")

    blocked, remaining = login_throttle.is_login_blocked(
        "exampleuser", "10.10.10.10"
    )
    assert blocked is True
    assert remaining > 0

    # Success clears the persisted record rather than only in-memory state.
    login_throttle.record_login_success("exampleuser", "10.10.10.10")
    assert login_throttle.is_login_blocked(
        "exampleuser", "10.10.10.10"
    ) == (False, 0)


def _create_recipe_audit_tables():
    conn = get_connection()
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
            INSERT INTO tbm_machines VALUES (1, 'P15');
            INSERT INTO machine_stages VALUES (1, 1, 'FIRST_STAGE');
            INSERT INTO recipes VALUES (1, 1, 1, 'R1', 'Recipe 1', 1, 'RELEASED', 'engineer');
            INSERT INTO parameter_definitions VALUES (1, 1, 1, 'WIDTH', 1, 0, 100);
            INSERT INTO recipe_parameter_values VALUES (1, 1, 1, 10, 0, CURRENT_TIMESTAMP);
            """
        )
        conn.commit()
    finally:
        conn.close()
    apply_v11_11_hardening_schema()


def test_parameter_audit_failure_rolls_back_value(monkeypatch):
    _create_recipe_audit_tables()

    def fail_audit(**_kwargs):
        raise RuntimeError("fault injection")

    monkeypatch.setattr(
        RecipeParameterAuditManager,
        "log_change",
        staticmethod(fail_audit),
    )
    result = RecipeParameterValueManager.update_recipe_value(
        value_id=1,
        new_value=25,
        changed_by="engineer",
        change_reason="Atomic audit test",
        user_role="ENGINEERING",
        change_source="SAFE_TEST",
    )

    assert result["success"] is False
    conn = get_connection()
    try:
        value = conn.execute(
            "SELECT parameter_value FROM recipe_parameter_values WHERE id=1"
        ).fetchone()[0]
    finally:
        conn.close()
    assert value == 10
