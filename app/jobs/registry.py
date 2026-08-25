from dataclasses import dataclass, field
from threading import RLock
from uuid import uuid4


STATUSES = {"queued", "running", "completed", "failed", "cancelled"}
STAGE_PROGRESS = {
    "queued": 0,
    "preprocessing": 10,
    "transcribing": 30,
    "normalizing": 45,
    "classifying": 65,
    "risk_search": 80,
    "finalizing": 90,
    "completed": 100,
}
STAGES = set(STAGE_PROGRESS) | {"failed", "cancelled"}
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
    progress: int = 0
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
        progress: int | None = None,
        result: dict | None = None,
        error: dict | None = None,
        metadata: dict | None = None,
    ) -> JobRecord:
        if status not in STATUSES or stage not in STAGES:
            raise InvalidJobTransition("Unknown job status or stage")
        if progress is not None and not 0 <= progress <= 100:
            raise InvalidJobTransition("Progress must be between 0 and 100")

        with self._lock:
            job = self._jobs[job_id]
            if status != job.status and status not in TRANSITIONS[job.status]:
                raise InvalidJobTransition(f"{job.status} -> {status} is not allowed")

            next_progress = progress
            if next_progress is None:
                next_progress = STAGE_PROGRESS.get(stage, job.progress)
            if status in {"failed", "cancelled"} and progress is None:
                next_progress = job.progress
            if next_progress < job.progress and status not in {"failed", "cancelled"}:
                raise InvalidJobTransition("Progress cannot decrease")

            job.status = status
            job.stage = stage
            job.progress = next_progress
            job.result = result if status == "completed" else None
            job.error = error if status == "failed" else None
            if metadata is not None:
                job.metadata = dict(metadata)
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
