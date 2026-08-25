import asyncio
import inspect
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
        timeout_seconds: float = 300.0,
    ):
        self.registry = registry
        self.analyzer = analyzer
        self.cleanup = cleanup
        self.job_lock = job_lock
        self.owner_key = owner_key
        self.task_registry = task_registry
        self.timeout_seconds = timeout_seconds

    async def run(self, job_id: str, audio: bytes, temp_path: str | None = None) -> None:
        try:
            self.registry.update(job_id, status="running", stage="preprocessing")
            result = await asyncio.wait_for(
                self._analyze(job_id, audio),
                timeout=self.timeout_seconds,
            )
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
                    "message": "\ubd84\uc11d \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.",
                },
            )
        finally:
            if self.cleanup is not None and temp_path is not None:
                self.cleanup.delete(temp_path)
            if self.job_lock is not None and self.owner_key is not None:
                self.job_lock.release(self.owner_key, job_id)
            if self.task_registry is not None:
                self.task_registry.remove(job_id)

    async def _analyze(self, job_id: str, audio: bytes):
        progress_analyze = getattr(self.analyzer, "analyze_with_progress", None)
        if progress_analyze is None:
            return await self.analyzer.analyze(audio)

        def report_stage(stage: str) -> None:
            self.registry.update(job_id, status="running", stage=stage)

        def report_progress(details: dict[str, int | str]) -> None:
            total = int(details.get("total_chunks", 0))
            completed = int(details.get("classified_chunks", 0))
            stage = str(details.get("stage", "classifying"))
            stage_order = {
                "queued": 0,
                "preprocessing": 1,
                "transcribing": 2,
                "normalizing": 3,
                "classifying": 4,
                "risk_search": 5,
                "finalizing": 6,
                "completed": 7,
            }
            job = self.registry.get(job_id)
            current_stage = job.stage if job is not None else stage
            effective_stage = stage
            if stage_order.get(stage, 0) < stage_order.get(current_stage, 0):
                effective_stage = current_stage
            if total <= 0:
                progress = job.progress if job is not None else 0
            elif stage == "transcribing":
                progress = 30 + round(5 * int(details.get("transcribed_chunks", 0)) / total)
            elif stage == "normalizing":
                progress = 45 + round(5 * int(details.get("normalized_chunks", 0)) / total)
            else:
                progress = 65 + round(15 * completed / total)
            progress = max(progress, job.progress if job is not None else progress)
            metadata = dict(details)
            metadata["stage"] = effective_stage
            self.registry.update(
                job_id,
                status="running",
                stage=effective_stage,
                progress=progress,
                metadata=metadata,
            )

        parameters = inspect.signature(progress_analyze).parameters
        if "report_progress" in parameters:
            return await progress_analyze(audio, report_stage, report_progress)
        return await progress_analyze(audio, report_stage)
