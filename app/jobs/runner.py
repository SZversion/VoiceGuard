from app.analysis.interfaces import Analyzer
from app.jobs.registry import InvalidJobTransition, JobRegistry


class JobRunner:
    def __init__(self, registry: JobRegistry, analyzer: Analyzer):
        self.registry = registry
        self.analyzer = analyzer

    async def run(self, job_id: str, audio: bytes) -> None:
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
        except Exception:
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
