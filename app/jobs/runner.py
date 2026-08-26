import logging

from app.analysis.interfaces import Analyzer
from app.jobs.registry import InvalidJobTransition, JobRegistry


logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(
        self,
        registry: JobRegistry,
        analyzer: Analyzer,
        cleanup=None,
        job_lock=None,
        owner_key=None,
        task_registry=None,
    ):
        self.registry = registry
        self.analyzer = analyzer
        self.cleanup = cleanup
        self.job_lock = job_lock
        self.owner_key = owner_key
        self.task_registry = task_registry

    async def run(self, job_id: str, audio: bytes, temp_path: str | None = None) -> None:
        try:
            self.registry.update(job_id, status="running", stage="preprocessing")
            result = await self.analyzer.analyze(audio)
            job = self.registry.get(job_id)
            if job is None or job.status == "cancelled":
                return
            self.registry.update(
                job_id,
                status="completed",
                stage="completed",
                result=dict(result),
            )
        except InvalidJobTransition:
            return
        except Exception as exc:
            logger.error(
                "Analysis job failed: %s (%s): %s",
                job_id,
                type(exc).__name__,
                str(exc),
            )
            job = self.registry.get(job_id)
            if job is None or job.status == "cancelled":
                return
            self.registry.update(
                job_id,
                status="failed",
                stage="failed",
                error={
                    "error_code": "ANALYSIS.FAILED",
                    "message": "분석 중 오류가 발생했습니다.",
                },
            )
        finally:
            if self.cleanup is not None and temp_path is not None:
                self.cleanup.delete(temp_path)
            if self.job_lock is not None and self.owner_key is not None:
                self.job_lock.release(self.owner_key, job_id)
            if self.task_registry is not None:
                self.task_registry.remove(job_id)
