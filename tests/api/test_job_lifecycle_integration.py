import asyncio
from io import BytesIO

import httpx

from app.api.main import app
from app.core.request_controls import DuplicateJobLock, IpHasher, RateLimiter
from app.jobs.cleanup import TempDataStore
from app.jobs.registry import JobRegistry
from app.jobs.task_registry import JobTaskRegistry


WAV = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 8


class SlowAnalyzer:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def analyze(self, audio: bytes) -> dict:
        self.started.set()
        await self.release.wait()
        return {"label": "normal"}


def test_cancel_api_cancels_running_analysis_task():
    async def scenario():
        analyzer = SlowAnalyzer()
        app.state.job_registry = JobRegistry()
        app.state.analyzer = analyzer
        app.state.temp_data_store = TempDataStore()
        app.state.ip_hasher = IpHasher("test-secret")
        app.state.job_lock = DuplicateJobLock()
        app.state.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
        app.state.task_registry = JobTaskRegistry()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            try:
                response = await client.post(
                    "/api/analyze",
                    files={"audio": ("call.wav", BytesIO(WAV), "audio/wav")},
                )
                await analyzer.started.wait()
                job_id = response.json()["job_id"]
                assert response.status_code == 202
                assert app.state.task_registry.get(job_id) is not None

                cancel_response = await client.delete(f"/api/analyze/{job_id}")

                assert cancel_response.status_code == 200
                assert cancel_response.json() == {"job_id": job_id, "status": "cancelled"}
                analyzer.release.set()
                await asyncio.sleep(0)
                assert app.state.task_registry.get(job_id) is None
            finally:
                analyzer.release.set()
                app.state.analyzer = None

    asyncio.run(scenario())
