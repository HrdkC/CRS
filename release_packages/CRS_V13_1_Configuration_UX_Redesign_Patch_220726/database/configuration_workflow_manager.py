"""Persistent progress tracking layered over live configuration readiness."""

import json

from database.audit_manager import AuditManager
from database.database import get_connection, transaction


class ConfigurationWorkflowConflict(RuntimeError):
    pass


class ConfigurationWorkflowManager:
    STEP_DEFINITIONS = (
        ("machine_stage", "Machine and Stage", "Confirm the configuration target."),
        ("plc_assignment", "PLC Assignment", "Assign one active PLC to this stage."),
        ("plc_tags", "PLC Tag Mapping", "Map all required CRS communication tags."),
        ("parameters", "Parameter Template", "Build and validate recipe parameters."),
        ("phase_controls", "Phase Controls", "Configure the allowed stage sequence."),
        ("first_recipe", "First Recipe", "Create the first controlled recipe record."),
        ("review", "Review and Readiness", "Resolve blockers and confirm readiness."),
    )
    VALID_MODES = {"STANDARD", "ADVANCED"}

    @staticmethod
    def _section_map(report):
        return {section["key"]: section for section in report.get("sections", [])}

    @staticmethod
    def _derived_status(step_key, report):
        sections = ConfigurationWorkflowManager._section_map(report)
        keys = {
            "machine_stage": ("machine_stage",),
            "plc_assignment": ("plc_registry",),
            "plc_tags": ("required_plc_tags", "required_tags"),
            "parameters": ("parameters",),
            "phase_controls": ("phase_master",),
            "first_recipe": ("recipes",),
        }.get(step_key, ())
        if step_key == "review":
            if report.get("blocking_count"):
                return "BLOCKED"
            if report.get("warning_count"):
                return "NEEDS_ATTENTION"
            return "COMPLETE"
        if step_key == "first_recipe":
            recipe_items = (sections.get("recipes") or {}).get("items", [])
            recipe_record = next(
                (item for item in recipe_items if item.get("label") == "Recipe records"),
                None,
            )
            if recipe_record and recipe_record.get("status") == "ok":
                return "COMPLETE"
            return "NEEDS_ATTENTION"
        matching = [sections[key] for key in keys if key in sections]
        if not matching:
            return "NOT_STARTED"
        severities = {section.get("severity") for section in matching}
        if "blocked" in severities:
            return "BLOCKED"
        if "warning" in severities:
            return "NEEDS_ATTENTION"
        return "COMPLETE"

    @staticmethod
    def _evidence(step_key, report):
        sections = ConfigurationWorkflowManager._section_map(report)
        related = {
            "machine_stage": ("machine_stage",),
            "plc_assignment": ("plc_registry",),
            "plc_tags": ("required_plc_tags", "required_tags"),
            "parameters": ("parameters",),
            "phase_controls": ("phase_master",),
            "first_recipe": ("recipes",),
            "review": tuple(sections),
        }.get(step_key, ())
        items = []
        for key in related:
            for item in (sections.get(key) or {}).get("items", []):
                items.append({
                    "label": item.get("label"),
                    "status": item.get("status"),
                    "detail": item.get("detail"),
                })
        return items

    @staticmethod
    def get_workflow(report):
        context = report["context"]
        conn = get_connection()
        try:
            workflow = conn.execute(
                "SELECT * FROM configuration_workflows WHERE stage_id = ?",
                (context["stage_id"],),
            ).fetchone()
            if not workflow:
                raise RuntimeError("Configuration workflow is not initialized.")
            workflow = dict(workflow)
            stored_steps = {
                row["step_key"]: dict(row)
                for row in conn.execute(
                    "SELECT * FROM configuration_workflow_steps WHERE workflow_id = ?",
                    (workflow["id"],),
                ).fetchall()
            }
        finally:
            conn.close()

        steps = []
        first_open = None
        for index, (key, title, summary) in enumerate(
            ConfigurationWorkflowManager.STEP_DEFINITIONS, start=1
        ):
            persisted = stored_steps.get(key, {})
            status = ConfigurationWorkflowManager._derived_status(key, report)
            if first_open is None and status != "COMPLETE":
                first_open = key
            evidence = ConfigurationWorkflowManager._evidence(key, report)
            blockers = [
                item["detail"] for item in evidence
                if item.get("status") in {"blocked", "warning"} and item.get("detail")
            ]
            steps.append({
                "number": index,
                "key": key,
                "title": title,
                "summary": summary,
                "status": status,
                "evidence": evidence,
                "blockers": blockers[:4],
                "last_viewed_by": persisted.get("last_viewed_by"),
                "last_viewed_at": persisted.get("last_viewed_at"),
                "completed_by": persisted.get("completed_by"),
                "completed_at": persisted.get("completed_at"),
            })
        current_key = workflow.get("current_step_key")
        if current_key not in {step["key"] for step in steps}:
            current_key = first_open or "review"
        completed = sum(step["status"] == "COMPLETE" for step in steps)
        workflow.update({
            "steps": steps,
            "current_step_key": current_key,
            "recommended_step_key": first_open or "review",
            "completed_steps": completed,
            "progress_percent": round((completed / len(steps)) * 100),
            "is_complete": completed == len(steps),
        })
        return workflow

    @staticmethod
    def record_step(
        workflow_id, step_key, username, expected_version, setup_mode=None,
        role="SYSTEM", request_metadata=None,
    ):
        valid_keys = {row[0] for row in ConfigurationWorkflowManager.STEP_DEFINITIONS}
        if step_key not in valid_keys:
            raise ValueError("Unknown configuration workflow step.")
        mode = (setup_mode or "STANDARD").strip().upper()
        if mode not in ConfigurationWorkflowManager.VALID_MODES:
            raise ValueError("Unknown configuration mode.")
        with transaction(immediate=True) as conn:
            current = conn.execute(
                "SELECT row_version FROM configuration_workflows WHERE id = ?",
                (int(workflow_id),),
            ).fetchone()
            if not current:
                raise ValueError("Configuration workflow was not found.")
            if int(current["row_version"]) != int(expected_version):
                raise ConfigurationWorkflowConflict(
                    "Configuration progress changed in another browser. Refresh and continue."
                )
            result = conn.execute(
                """
                UPDATE configuration_workflows
                SET current_step_key = ?, setup_mode = ?, updated_by = ?,
                    updated_at = CURRENT_TIMESTAMP, row_version = row_version + 1
                WHERE id = ? AND row_version = ?
                """,
                (step_key, mode, username, int(workflow_id), int(expected_version)),
            )
            if result.rowcount != 1:
                raise ConfigurationWorkflowConflict(
                    "Configuration progress changed in another browser. Refresh and continue."
                )
            conn.execute(
                """
                UPDATE configuration_workflow_steps
                SET last_viewed_by = ?, last_viewed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP, row_version = row_version + 1
                WHERE workflow_id = ? AND step_key = ?
                """,
                (username, int(workflow_id), step_key),
            )
            metadata = request_metadata or {}
            AuditManager.log_event(
                username=username,
                role=role,
                action="CONFIGURATION_WORKFLOW_PROGRESS",
                change_source="GUIDED_CONFIGURATION",
                record_id=int(workflow_id),
                old_value=f"row_version={expected_version}",
                new_value=f"step={step_key}; mode={mode}",
                reason="Resume guided configuration workflow",
                user_agent=metadata.get("user_agent"),
                forwarded_for=metadata.get("forwarded_for"),
                request_host=metadata.get("request_host"),
                _connection=conn,
            )

    @staticmethod
    def save_evidence(
        workflow_id, report, username, role="SYSTEM", request_metadata=None
    ):
        """Persist validated evidence after an explicit review action."""
        with transaction(immediate=True) as conn:
            complete = True
            for key, _title, _summary in ConfigurationWorkflowManager.STEP_DEFINITIONS:
                status = ConfigurationWorkflowManager._derived_status(key, report)
                evidence = ConfigurationWorkflowManager._evidence(key, report)
                complete = complete and status == "COMPLETE"
                blocker = "; ".join(
                    item.get("detail") or ""
                    for item in evidence
                    if item.get("status") in {"blocked", "warning"}
                )[:1000]
                conn.execute(
                    """
                    UPDATE configuration_workflow_steps
                    SET status = ?, evidence_json = ?, blocker_summary = ?,
                        completed_by = CASE WHEN ? = 'COMPLETE' THEN ? ELSE NULL END,
                        completed_at = CASE WHEN ? = 'COMPLETE' THEN CURRENT_TIMESTAMP ELSE NULL END,
                        updated_at = CURRENT_TIMESTAMP, row_version = row_version + 1
                    WHERE workflow_id = ? AND step_key = ?
                    """,
                    (
                        status, json.dumps(evidence, default=str), blocker,
                        status, username, status, int(workflow_id), key,
                    ),
                )
            conn.execute(
                """
                UPDATE configuration_workflows
                SET status = ?, completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END,
                    updated_by = ?, updated_at = CURRENT_TIMESTAMP,
                    row_version = row_version + 1
                WHERE id = ?
                """,
                ("COMPLETE" if complete else "IN_PROGRESS", int(complete), username, int(workflow_id)),
            )
            metadata = request_metadata or {}
            AuditManager.log_event(
                username=username,
                role=role,
                action="CONFIGURATION_REVIEW_SAVED",
                change_source="GUIDED_CONFIGURATION",
                record_id=int(workflow_id),
                old_value="Review evidence refreshed",
                new_value=(
                    f"status={'COMPLETE' if complete else 'IN_PROGRESS'}; "
                    f"blocked={report.get('blocking_count', 0)}; "
                    f"warnings={report.get('warning_count', 0)}"
                ),
                reason="Save validated machine/stage configuration evidence",
                user_agent=metadata.get("user_agent"),
                forwarded_for=metadata.get("forwarded_for"),
                request_host=metadata.get("request_host"),
                _connection=conn,
            )
