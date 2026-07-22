from pathlib import Path


def _reset_schema_cache():
    import database.hardening_schema_manager as schema

    schema._SCHEMA_READY_VERIFIED = False
    return schema


def test_terminal_result_is_persisted_after_last_progress_update():
    schema = _reset_schema_cache()
    schema.apply_v11_11_hardening_schema()

    from database.plc_operation_job_manager import PLCOperationJobManager

    job_id = PLCOperationJobManager.create_job(
        recipe_id=13,
        plc_id=5,
        operation="recipe_restore",
        title="Recipe Restore",
        username="hardik",
        user_role="ADMIN",
    )

    running = {
        "operation": "recipe_restore",
        "title": "Recipe Restore",
        "success": False,
        "status": "RUNNING",
        "progress_percent": 93,
        "current_step": "Immediate CRS buffer verified",
        "steps": [],
        "errors": [],
        "warnings": [],
        "metrics": {},
    }
    assert PLCOperationJobManager.update_from_result(
        job_id,
        running,
        status_override="RUNNING",
    )

    final = dict(running)
    final.update({
        "success": True,
        "status": "SUCCESS",
        "progress_percent": 100,
        "current_step": "Recipe restored to CRS buffer",
    })
    assert PLCOperationJobManager.ensure_terminal_state(job_id, final)

    job = PLCOperationJobManager.get_job(job_id)
    assert job["status"] == "SUCCESS"
    assert job["progress_percent"] == 100
    assert job["completed_at"] is not None
    assert job["result"]["current_step"] == "Recipe restored to CRS buffer"


def test_orphaned_running_job_is_recovered_and_completed():
    schema = _reset_schema_cache()
    schema.apply_v11_11_hardening_schema()

    from database.plc_operation_job_manager import PLCOperationJobManager

    job_id = PLCOperationJobManager.create_job(
        recipe_id=13,
        plc_id=5,
        operation="recipe_restore",
        title="Recipe Restore",
        username="hardik",
        user_role="ADMIN",
    )
    running = {
        "operation": "recipe_restore",
        "title": "Recipe Restore",
        "success": False,
        "status": "RUNNING",
        "progress_percent": 93,
        "current_step": "Immediate CRS buffer verified",
        "steps": [],
        "errors": [],
        "warnings": [],
        "metrics": {},
    }
    assert PLCOperationJobManager.update_from_result(
        job_id,
        running,
        status_override="RUNNING",
    )

    assert PLCOperationJobManager.recover_orphaned_job(job_id)
    job = PLCOperationJobManager.get_job(job_id)
    assert job["status"] == "INTERRUPTED"
    assert job["progress_percent"] == 100
    assert job["completed_at"] is not None
    assert "orphaned job was recovered" in job["current_step"]


def test_status_polling_uses_no_store_and_retryable_response_handling():
    source = Path(
        "flask_app/static/js/pages/download-preparation.js"
    ).read_text(encoding="utf-8")

    assert 'cache: "no-store"' in source
    assert 'credentials: "same-origin"' in source
    assert "payload.retryable" in source
    assert "status connection (attempt " in source


def test_transient_locked_database_operation_is_retried():
    import sqlite3

    from database.plc_operation_job_manager import PLCOperationJobManager

    attempts = {"count": 0}

    def temporarily_locked():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    assert PLCOperationJobManager._with_database_retry(
        temporarily_locked,
        attempts=5,
        initial_delay=0.001,
    ) == "ok"
    assert attempts["count"] == 3
