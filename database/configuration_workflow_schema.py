"""Controlled schema upgrade for the guided configuration workflow."""

import json

from database.database import transaction


CONFIGURATION_WORKFLOW_SCHEMA_VERSION = "CRS_V13_CONFIGURATION_WORKFLOW_001"


def apply_configuration_workflow_schema():
    with transaction(immediate=True) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS configuration_workflows
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                stage_id INTEGER NOT NULL,
                current_step_key TEXT NOT NULL DEFAULT 'machine_stage',
                setup_mode TEXT NOT NULL DEFAULT 'STANDARD',
                status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
                row_version INTEGER NOT NULL DEFAULT 1,
                started_by TEXT,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                UNIQUE(machine_id, stage_id),
                FOREIGN KEY(machine_id) REFERENCES tbm_machines(id),
                FOREIGN KEY(stage_id) REFERENCES machine_stages(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS configuration_workflow_steps
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                step_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'NOT_STARTED',
                evidence_json TEXT,
                blocker_summary TEXT,
                row_version INTEGER NOT NULL DEFAULT 1,
                last_viewed_by TEXT,
                last_viewed_at DATETIME,
                completed_by TEXT,
                completed_at DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workflow_id, step_key),
                FOREIGN KEY(workflow_id) REFERENCES configuration_workflows(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_configuration_workflow_stage "
            "ON configuration_workflows(stage_id, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_configuration_step_status "
            "ON configuration_workflow_steps(workflow_id, status)"
        )

        stages = conn.execute(
            """
            SELECT s.id AS stage_id, s.machine_id
            FROM machine_stages s
            INNER JOIN tbm_machines m ON m.id = s.machine_id
            """
        ).fetchall()
        step_keys = (
            "machine_stage", "plc_assignment", "plc_tags", "parameters",
            "phase_controls", "first_recipe", "review",
        )
        for stage in stages:
            conn.execute(
                """
                INSERT OR IGNORE INTO configuration_workflows
                    (machine_id, stage_id, current_step_key, status, started_by)
                VALUES (?, ?, 'machine_stage', 'IN_PROGRESS', 'MIGRATION')
                """,
                (stage["machine_id"], stage["stage_id"]),
            )
            workflow = conn.execute(
                "SELECT id FROM configuration_workflows WHERE stage_id = ?",
                (stage["stage_id"],),
            ).fetchone()
            for step_key in step_keys:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO configuration_workflow_steps
                        (workflow_id, step_key, evidence_json)
                    VALUES (?, ?, ?)
                    """,
                    (workflow["id"], step_key, json.dumps({"source": "BACKFILL"})),
                )

        conn.execute(
            """
            INSERT INTO schema_version(version, description)
            SELECT ?, ?
            WHERE NOT EXISTS
            (
                SELECT 1 FROM schema_version WHERE version = ?
            )
            """,
            (
                CONFIGURATION_WORKFLOW_SCHEMA_VERSION,
                "Persistent seven-step machine/stage configuration workflow",
                CONFIGURATION_WORKFLOW_SCHEMA_VERSION,
            ),
        )


def assert_configuration_workflow_schema_ready():
    with transaction() as conn:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    required = {"configuration_workflows", "configuration_workflow_steps"}
    missing = sorted(required - names)
    if missing:
        raise RuntimeError(
            "Configuration workflow schema is not ready. Run "
            "scripts/upgrade_configuration_workflow_v13.py. Missing: "
            + ", ".join(missing)
        )
