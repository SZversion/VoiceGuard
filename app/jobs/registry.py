from dataclasses import dataclass, field
from threading import RLock
from uuid import uuid4


STATUSES = {"queued", "running", "completed", "failed", "cancelled"}
STAGES = {"queued", "preprocessing", "transcribing", "classifying", "finalizing", "completed", "failed", "cancelled"}
TRANSITIONS = {
    "queued": {"running", "failed", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


class InvalidJobTransition(ValueError):
    pass


@dataclass
class JobRecord:
    job_id: str
    owner_key: str
    status: str = "queued"
    stage: str = "queued"
    result: dict | None = None
    error: dict | None = None
    metadata: dict = field(default_factory=dict)


class JobRegistry:
    def __init__(self):
        self._jobs: dict[str, JobRecord] = {}
        self._lock = RLock()

    def create(self, owner_key: str) -> JobRecord:
        job = JobRecord(job_id=f"job_{uuid4().hex}", owner_key=owner_key)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: str,
        stage: str,
        result: dict | None = None,
        error: dict | None = None,
    ) -> JobRecord:
        if status not in STATUSES or stage not in STAGES:
            raise InvalidJobTransition("Unknown job status or stage")

        with self._lock:
            job = self._jobs[job_id]
            if status != job.status and status not in TRANSITIONS[job.status]:
                raise InvalidJobTransition(f"{job.status} -> {status} is not allowed")
            job.status = status
            job.stage = stage
            job.result = result if status == "completed" else None
            job.error = error if status == "failed" else None
            return job

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            if job.status not in {"queued", "running"}:
                return False
            job.status = "cancelled"
            job.stage = "cancelled"
            job.result = None
            job.error = None
            return True
