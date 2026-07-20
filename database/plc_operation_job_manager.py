import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from database.hardening_schema_manager import assert_v11_11_hardening_schema_ready
from database.orm_models import PLCOperationJob
from database.recipe_resource_lock_manager import RecipeResourceLockManager
from database.sqlalchemy_db import session_scope


class PLCOperationJobManager:
    FINAL_STATUSES = {
        "SUCCESS", "BLOCKED", "ERROR", "INTERRUPTED", "CANCELLED",
        "RECOVERY_REQUIRED",
    }
    ACTIVE_STATUSES = {"QUEUED", "RUNNING"}

    @staticmethod
    def ensure_table():
        assert_v11_11_hardening_schema_ready()

    @staticmethod
    def create_job(
        recipe_id,
        plc_id,
        operation,
        title,
        username,
        user_role,
        recipe_lock_id=None,
        plc_lock_id=None,
        correlation_id=None,
    ):
        PLCOperationJobManager.ensure_table()
        job_id = uuid.uuid4().hex
        correlation_id = correlation_id or uuid.uuid4().hex
        initial_result = {
            "operation": operation,
            "title": title,
            "success": False,
            "status": "QUEUED",
            "progress_percent": 0,
            "current_step": "Queued for durable PLC worker",
            "steps": [],
            "errors": [],
            "warnings": [],
            "metrics": {},
            "correlation_id": correlation_id,
            "payload_compare": {
                "checked": False, "matched": False,
                "mismatch_count": 0, "mismatches": [],
            },
            "destination_compare": {
                "checked": False, "matched": False,
                "mismatch_count": 0, "mismatches": [],
            },
        }
        with session_scope() as session:
            session.add(
                PLCOperationJob(
                    id=job_id,
                    recipe_id=recipe_id,
                    plc_id=plc_id,
                    operation=operation,
                    title=title,
                    status="QUEUED",
                    success=0,
                    progress_percent=0,
                    current_step="Queued for durable PLC worker",
                    started_by=username,
                    user_role=user_role,
                    result_json=json.dumps(initial_result, default=str),
                    correlation_id=correlation_id,
                    recipe_lock_id=recipe_lock_id,
                    plc_lock_id=plc_lock_id,
                    heartbeat_at=func.current_timestamp(),
                )
            )
        return job_id

    @staticmethod
    def get_active_for_plc(plc_id, stale_minutes=30):
        PLCOperationJobManager.ensure_table()
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=stale_minutes)
        with session_scope() as session:
            job = session.execute(
                select(PLCOperationJob)
                .where(PLCOperationJob.plc_id == plc_id)
                .where(PLCOperationJob.completed_at.is_(None))
                .where(PLCOperationJob.status.in_(list(PLCOperationJobManager.ACTIVE_STATUSES)))
                .where(func.coalesce(PLCOperationJob.heartbeat_at, PLCOperationJob.updated_at) >= cutoff)
                .order_by(PLCOperationJob.created_at.desc())
                .limit(1)
            ).scalars().first()
            return PLCOperationJobManager.to_dict(job) if job else None

    @staticmethod
    def claim_next_job(worker_id):
        """Atomically claim the oldest queued job for a durable worker."""
        PLCOperationJobManager.ensure_table()
        for _ in range(5):
            with session_scope() as session:
                job_id = session.execute(
                    select(PLCOperationJob.id)
                    .where(PLCOperationJob.status == "QUEUED")
                    .order_by(PLCOperationJob.created_at.asc())
                    .limit(1)
                ).scalar_one_or_none()
                if not job_id:
                    return None
                result = session.execute(
                    update(PLCOperationJob)
                    .where(PLCOperationJob.id == job_id)
                    .where(PLCOperationJob.status == "QUEUED")
                    .values(
                        status="RUNNING",
                        worker_id=worker_id,
                        current_step="Claimed by durable PLC worker",
                        heartbeat_at=func.current_timestamp(),
                        updated_at=func.current_timestamp(),
                    )
                )
                if result.rowcount == 1:
                    job = session.get(PLCOperationJob, job_id)
                    return PLCOperationJobManager.to_dict(job)
        return None

    @staticmethod
    def heartbeat(job_id, worker_id=None):
        PLCOperationJobManager.ensure_table()
        with session_scope() as session:
            query = (
                update(PLCOperationJob)
                .where(PLCOperationJob.id == job_id)
                .where(PLCOperationJob.status == "RUNNING")
            )
            if worker_id:
                query = query.where(PLCOperationJob.worker_id == worker_id)
            result = session.execute(
                query.values(
                    heartbeat_at=func.current_timestamp(),
                    updated_at=func.current_timestamp(),
                )
            )
            return result.rowcount == 1

    @staticmethod
    def update_from_result(job_id, result, status_override=None, completed=False):
        if not job_id:
            return
        PLCOperationJobManager.ensure_table()
        status = status_override or result.get("status", "RUNNING")
        with session_scope() as session:
            job = session.get(PLCOperationJob, job_id)
            if not job:
                return
            job.status = status
            job.success = 1 if result.get("success") else 0
            job.progress_percent = int(result.get("progress_percent", 0) or 0)
            job.current_step = result.get("current_step", "")
            job.result_json = json.dumps(result, default=str)
            job.updated_at = func.current_timestamp()
            job.heartbeat_at = func.current_timestamp()
            if completed or status in PLCOperationJobManager.FINAL_STATUSES:
                job.completed_at = func.current_timestamp()

    @staticmethod
    def fail_job(job_id, message):
        result = {
            "operation": "",
            "title": "PLC Buffer Operation",
            "success": False,
            "status": "ERROR",
            "progress_percent": 5,
            "current_step": "Operation failed",
            "steps": [{
                "label": "Operation failed", "status": "FAILED",
                "message": message, "percent": 5,
            }],
            "errors": [message],
            "warnings": [],
            "metrics": {},
            "payload_compare": {"checked": False, "matched": False, "mismatch_count": 0, "mismatches": []},
            "destination_compare": {"checked": False, "matched": False, "mismatch_count": 0, "mismatches": []},
        }
        PLCOperationJobManager.update_from_result(
            job_id=job_id, result=result, status_override="ERROR", completed=True
        )

    @staticmethod
    def recover_stale_jobs(stale_minutes=10, recovery_reason="APPLICATION_STARTUP_RECOVERY"):
        """Close orphan active jobs and release their recorded resource locks."""
        PLCOperationJobManager.ensure_table()
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=max(1, int(stale_minutes)))
        recovered = []
        with session_scope() as session:
            jobs = session.execute(
                select(PLCOperationJob)
                .where(PLCOperationJob.status.in_(list(PLCOperationJobManager.ACTIVE_STATUSES)))
                .where(func.coalesce(PLCOperationJob.heartbeat_at, PLCOperationJob.updated_at) < cutoff)
            ).scalars().all()
            for job in jobs:
                job.status = "INTERRUPTED"
                job.success = 0
                job.current_step = "Recovered after stale worker/application restart"
                job.recovery_note = recovery_reason
                job.completed_at = func.current_timestamp()
                job.updated_at = func.current_timestamp()
                recovered.append({
                    "id": job.id,
                    "recipe_lock_id": job.recipe_lock_id,
                    "plc_lock_id": job.plc_lock_id,
                })
        for item in recovered:
            RecipeResourceLockManager.release_lock(
                item.get("recipe_lock_id"), reason="STALE_PLC_JOB_RECOVERED"
            )
            RecipeResourceLockManager.release_lock(
                item.get("plc_lock_id"), reason="STALE_PLC_JOB_RECOVERED"
            )
        return len(recovered)

    @staticmethod
    def get_job(job_id):
        PLCOperationJobManager.ensure_table()
        with session_scope() as session:
            job = session.get(PLCOperationJob, job_id)
            return PLCOperationJobManager.to_dict(job) if job else None

    @staticmethod
    def get_recent_for_recipe(recipe_id, limit=8):
        PLCOperationJobManager.ensure_table()
        with session_scope() as session:
            jobs = session.execute(
                select(PLCOperationJob)
                .where(PLCOperationJob.recipe_id == recipe_id)
                .order_by(PLCOperationJob.created_at.desc(), PLCOperationJob.updated_at.desc())
                .limit(limit)
            ).scalars().all()
            return [PLCOperationJobManager.to_dict(job) for job in jobs]

    @staticmethod
    def to_dict(job):
        if not job:
            return None
        data = job.to_dict()
        for key in ["created_at", "updated_at", "completed_at", "heartbeat_at"]:
            if data.get(key) is not None:
                data[key] = str(data[key])
        data["result"] = PLCOperationJobManager.parse_result(data.get("result_json"))
        return data

    @staticmethod
    def parse_result(value):
        if not value:
            return {}
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return {"raw": str(value)}
