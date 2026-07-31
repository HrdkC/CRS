from pathlib import Path

import pytest

from database import database as database_module
from database.configuration_workflow_manager import (
    ConfigurationWorkflowConflict,
    ConfigurationWorkflowManager,
)
from database.configuration_workflow_schema import apply_configuration_workflow_schema


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _schema():
    conn = database_module.get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE schema_version
            (id INTEGER PRIMARY KEY, version TEXT UNIQUE, description TEXT, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE tbm_machines
            (id INTEGER PRIMARY KEY, machine_code TEXT, description TEXT, active INTEGER DEFAULT 1);
            CREATE TABLE machine_stages
            (id INTEGER PRIMARY KEY, machine_id INTEGER, stage_type TEXT, description TEXT, active INTEGER DEFAULT 1);
            CREATE TABLE audit_log
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                username TEXT, role TEXT, workstation_name TEXT, client_ip TEXT,
                plc_name TEXT, recipe_code TEXT, recipe_version INTEGER,
                record_id INTEGER, parameter_name TEXT, old_value TEXT,
                new_value TEXT, action TEXT, change_source TEXT, reason TEXT,
                user_agent TEXT, forwarded_for TEXT, request_host TEXT,
                correlation_id TEXT
            );
            INSERT INTO tbm_machines VALUES (1, 'P01', 'TBM P01', 1);
            INSERT INTO machine_stages VALUES (10, 1, 'FIRST_STAGE', 'First Stage', 1);
            """
        )
        conn.commit()
    finally:
        conn.close()
    apply_configuration_workflow_schema()


def _report():
    return {
        "context": {"machine_id": 1, "stage_id": 10},
        "blocking_count": 1,
        "warning_count": 1,
        "sections": [
            {"key": "machine_stage", "severity": "ok", "items": []},
            {"key": "plc_registry", "severity": "ok", "items": []},
            {"key": "required_tags", "severity": "blocked", "items": [
                {"label": "Recipe Data", "status": "blocked", "detail": "RECIPE_DATA is not mapped."}
            ]},
            {"key": "parameters", "severity": "warning", "items": []},
            {"key": "phase_master", "severity": "ok", "items": []},
            {"key": "recipes", "severity": "warning", "items": [
                {"label": "Recipe records", "status": "ok", "detail": "1 recipe(s)."},
                {"label": "Current production recipe", "status": "warning", "detail": "None."},
            ]},
        ],
    }


def test_schema_backfills_workflow_and_live_status(tmp_path, monkeypatch):
    monkeypatch.setattr(database_module, "DATABASE_PATH", tmp_path / "workflow.db")
    _schema()
    workflow = ConfigurationWorkflowManager.get_workflow(_report())
    assert len(workflow["steps"]) == 7
    assert workflow["steps"][0]["status"] == "COMPLETE"
    assert workflow["steps"][2]["status"] == "BLOCKED"
    assert workflow["steps"][5]["status"] == "COMPLETE"
    assert workflow["recommended_step_key"] == "plc_tags"


def test_progress_update_uses_optimistic_version(tmp_path, monkeypatch):
    monkeypatch.setattr(database_module, "DATABASE_PATH", tmp_path / "workflow_version.db")
    _schema()
    workflow = ConfigurationWorkflowManager.get_workflow(_report())
    ConfigurationWorkflowManager.record_step(
        workflow["id"], "plc_tags", "hardik", workflow["row_version"], "STANDARD"
    )
    with pytest.raises(ConfigurationWorkflowConflict):
        ConfigurationWorkflowManager.record_step(
            workflow["id"], "parameters", "hardik", workflow["row_version"], "STANDARD"
        )


def test_guided_templates_keep_advanced_tools_separate():
    source = (PROJECT_ROOT / "flask_app/templates/configuration/setup_workflow.html").read_text(encoding="utf-8")
    assert "Step {{ active_step.number }} of 7" in source
    assert "Open Engineering Tools" in source
    assert "Build from Configured Recipe Array" in source
    assert "CAP_STRIP_SIDE and BT_SIDE only" in source
    assert "setup-mode-switch" not in source
    assert ">Standard</button>" not in source
    assert ">Advanced</button>" not in source
    assert 'name="setup_mode" value="STANDARD"' in source
    assert "section['items']" in source
    assert "section.items" not in source
    option_source = (
        PROJECT_ROOT / "flask_app/templates/parameters/template_setup_options.html"
    ).read_text(encoding="utf-8")
    assert "Preview Template Rows" in option_source
    assert "Copy Compatible Template" in option_source
    assert "Preview Only" in option_source
