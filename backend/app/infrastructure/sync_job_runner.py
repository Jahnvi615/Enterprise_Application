import uuid
from datetime import datetime, timezone
from app.core.interfaces import JobRunnerInterface
import structlog

logger = structlog.get_logger()


class SyncJobRunner(JobRunnerInterface):
    """Runs jobs synchronously for local development. Swap to Celery for production."""

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._handlers: dict[str, callable] = {}

    def register(self, task_name: str, handler: callable):
        self._handlers[task_name] = handler

    def submit(self, task_name: str, payload: dict) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "id": job_id,
            "task": task_name,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
            "error": None,
        }

        handler = self._handlers.get(task_name)
        if not handler:
            self._jobs[job_id]["status"] = "failed"
            self._jobs[job_id]["error"] = f"Unknown task: {task_name}"
            logger.error("unknown_task", task=task_name, job_id=job_id)
            return job_id

        try:
            self._jobs[job_id]["status"] = "running"
            logger.info("job_started", task=task_name, job_id=job_id)
            result = handler(**payload)
            self._jobs[job_id]["status"] = "completed"
            self._jobs[job_id]["result"] = result
            logger.info("job_completed", task=task_name, job_id=job_id)
        except Exception as e:
            self._jobs[job_id]["status"] = "failed"
            self._jobs[job_id]["error"] = str(e)
            logger.error("job_failed", task=task_name, job_id=job_id, error=str(e))

        return job_id

    def get_status(self, job_id: str) -> dict:
        return self._jobs.get(job_id, {"id": job_id, "status": "not_found"})

    def cancel(self, job_id: str) -> bool:
        if job_id in self._jobs and self._jobs[job_id]["status"] == "pending":
            self._jobs[job_id]["status"] = "cancelled"
            return True
        return False
