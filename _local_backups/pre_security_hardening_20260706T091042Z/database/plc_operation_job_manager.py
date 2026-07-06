import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import (
    func,
    select
)

from database.orm_models import (
    PLCOperationJob
)

from database.sqlalchemy_db import (
    Base,
    engine,
    session_scope
)


class PLCOperationJobManager:

    @staticmethod
    def ensure_table():

        Base.metadata.create_all(
            bind=engine,
            tables=[
                PLCOperationJob.__table__
            ]
        )

    @staticmethod
    def create_job(

        recipe_id,

        plc_id,

        operation,

        title,

        username,

        user_role

    ):

        PLCOperationJobManager.ensure_table()

        job_id = uuid.uuid4().hex

        initial_result = {
            "operation": operation,
            "title": title,
            "success": False,
            "status": "QUEUED",
            "progress_percent": 0,
            "current_step": "Queued",
            "steps": [],
            "errors": [],
            "warnings": [],
            "metrics": {},
            "payload_compare": {
                "checked": False,
                "matched": False,
                "mismatch_count": 0,
                "mismatches": []
            },
            "destination_compare": {
                "checked": False,
                "matched": False,
                "mismatch_count": 0,
                "mismatches": []
            }
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
                    current_step="Queued",
                    started_by=username,
                    user_role=user_role,
                    result_json=json.dumps(
                        initial_result,
                        default=str
                    )
                )
            )

        return job_id


    @staticmethod
    def get_active_for_plc(

        plc_id,

        stale_minutes=30

    ):

        PLCOperationJobManager.ensure_table()

        cutoff = datetime.utcnow() - timedelta(
            minutes=stale_minutes
        )

        with session_scope() as session:

            job = session.execute(
                select(
                    PLCOperationJob
                )
                .where(
                    PLCOperationJob.plc_id == plc_id
                )
                .where(
                    PLCOperationJob.completed_at.is_(None)
                )
                .where(
                    PLCOperationJob.status.in_(
                        [
                            "QUEUED",
                            "RUNNING"
                        ]
                    )
                )
                .where(
                    PLCOperationJob.updated_at >= cutoff
                )
                .order_by(
                    PLCOperationJob.created_at.desc(),
                    PLCOperationJob.updated_at.desc()
                )
                .limit(
                    1
                )
            ).scalars().first()

            if not job:

                return None

            return PLCOperationJobManager.to_dict(
                job
            )

    @staticmethod
    def update_from_result(

        job_id,

        result,

        status_override=None,

        completed=False

    ):

        if not job_id:

            return

        PLCOperationJobManager.ensure_table()

        status = (
            status_override
            if status_override
            else result.get(
                "status",
                "RUNNING"
            )
        )

        with session_scope() as session:

            job = session.get(
                PLCOperationJob,
                job_id
            )

            if not job:

                return

            job.status = status
            job.success = 1 if result.get("success") else 0
            job.progress_percent = int(
                result.get(
                    "progress_percent",
                    0
                )
                or
                0
            )
            job.current_step = result.get(
                "current_step",
                ""
            )
            job.result_json = json.dumps(
                result,
                default=str
            )
            job.updated_at = func.current_timestamp()

            if completed:

                job.completed_at = func.current_timestamp()

    @staticmethod
    def fail_job(

        job_id,

        message

    ):

        result = {
            "operation": "",
            "title": "PLC Buffer Operation",
            "success": False,
            "status": "ERROR",
            "progress_percent": 5,
            "current_step": message,
            "steps": [
                {
                    "label": "Operation failed",
                    "status": "FAILED",
                    "message": message,
                    "percent": 5
                }
            ],
            "errors": [
                message
            ],
            "warnings": [],
            "metrics": {},
            "payload_compare": {
                "checked": False,
                "matched": False,
                "mismatch_count": 0,
                "mismatches": []
            },
            "destination_compare": {
                "checked": False,
                "matched": False,
                "mismatch_count": 0,
                "mismatches": []
            }
        }

        PLCOperationJobManager.update_from_result(
            job_id=job_id,
            result=result,
            status_override="ERROR",
            completed=True
        )

    @staticmethod
    def get_job(

        job_id

    ):

        PLCOperationJobManager.ensure_table()

        with session_scope() as session:

            job = session.get(
                PLCOperationJob,
                job_id
            )

            if not job:

                return None

            return PLCOperationJobManager.to_dict(
                job
            )

    @staticmethod
    def get_recent_for_recipe(

        recipe_id,

        limit=8

    ):

        PLCOperationJobManager.ensure_table()

        with session_scope() as session:

            jobs = session.execute(
                select(
                    PLCOperationJob
                )
                .where(
                    PLCOperationJob.recipe_id == recipe_id
                )
                .order_by(
                    PLCOperationJob.created_at.desc(),
                    PLCOperationJob.updated_at.desc()
                )
                .limit(
                    limit
                )
            ).scalars().all()

            return [
                PLCOperationJobManager.to_dict(
                    job
                )
                for job in jobs
            ]

    @staticmethod
    def to_dict(

        job

    ):

        data = job.to_dict()

        for key in [
            "created_at",
            "updated_at",
            "completed_at"
        ]:

            value = data.get(
                key
            )

            if value is not None:

                data[key] = str(
                    value
                )

        data["result"] = PLCOperationJobManager.parse_result(
            data.get(
                "result_json"
            )
        )

        return data

    @staticmethod
    def parse_result(

        value

    ):

        if not value:

            return {}

        try:

            return json.loads(
                value
            )

        except Exception:

            return {}
