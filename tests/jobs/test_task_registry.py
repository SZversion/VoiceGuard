import asyncio

from app.jobs.task_registry import JobTaskRegistry


def test_task_registry_cancels_running_task_and_removes_it():
    async def scenario():
        registry = JobTaskRegistry()
        started = asyncio.Event()

        async def work():
            started.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(work())
        registry.register("job-1", task)
        await started.wait()

        assert registry.cancel("job-1") is True
        assert task.cancelled() is False
        await asyncio.gather(task, return_exceptions=True)
        assert registry.get("job-1") is None

    asyncio.run(scenario())


def test_task_registry_returns_false_for_unknown_job():
    assert JobTaskRegistry().cancel("job-missing") is False
