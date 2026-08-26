import time
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.jobs.cleanup import TempDataStore


WAV = b"RIFF" + bytes(4) + b"WAVE" + bytes(8)


class FakeTranscriber:
    async def transcribe(self, audio: bytes) -> str:
        return "정상적인 상담 내용입니다."


class FailingTranscriber:
    async def transcribe(self, audio: bytes) -> str:
        raise RuntimeError("stt failed")


class FakeClassifier:
    def classify(self, transcript: str):
        return type(
            "Result",
            (),
            {
                "label": "normal",
                "suspicion_score": 0.1,
            },
        )()


def wait_for_status(client: TestClient, job_id: str, expected: str) -> dict:
    for _ in range(50):
        response = client.get(f"/api/analyze/{job_id}/status")
        payload = response.json()
        if payload["status"] == expected:
            return payload
        time.sleep(0.01)
    raise AssertionError(f"job did not reach {expected}: {payload}")


def build_app(transcriber):
    return create_app(
        stt_loader=lambda: transcriber,
        classifier_loader=FakeClassifier,
    )


def upload(client: TestClient):
    return client.post(
        "/api/analyze",
        files={"audio": ("call.wav", BytesIO(WAV), "audio/wav")},
    )


def test_analysis_pipeline_completes_and_returns_result(tmp_path: Path):
    test_app = build_app(FakeTranscriber())
    test_app.state.temp_data_store = TempDataStore(str(tmp_path))

    with TestClient(test_app) as client:
        create_response = upload(client)

        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        status = wait_for_status(client, job_id, "completed")
        assert status == {
            "job_id": job_id,
            "status": "completed",
            "stage": "completed",
        }

        result_response = client.get(f"/api/analyze/{job_id}/result")

        assert result_response.status_code == 200
        assert result_response.json() == {
            "job_id": job_id,
            "result": {
                "raw_transcript": "정상적인 상담 내용입니다.",
                "corrected_transcript": "정상적인 상담 내용입니다.",
                "corrections": [],
                "label": "normal",
                "suspicion_score": 0.1,
                "classification_status": "classified",
                "quality": {"usable": True, "score": 1.0, "reason": None},
                "reference_segments": [],
                "guidance": "검토가 필요한 경우 금융기관 공식 채널로 확인하세요.",
            },
        }
        assert list(tmp_path.iterdir()) == []
        assert test_app.state.task_registry.get(job_id) is None

        second_response = upload(client)
        assert second_response.status_code == 202


def test_analysis_uses_default_domain_correction_before_classification(tmp_path: Path):
    class DomainTranscriber:
        async def transcribe(self, audio: bytes) -> str:
            return "검찰 청을 사칭했습니다."

    class RecordingClassifier:
        received_transcript = None

        def classify(self, transcript: str):
            self.received_transcript = transcript
            return type(
                "Result",
                (),
                {"label": "voice_phishing", "suspicion_score": 0.9},
            )()

    classifier = RecordingClassifier()
    test_app = create_app(
        stt_loader=DomainTranscriber,
        classifier_loader=lambda: classifier,
    )
    test_app.state.temp_data_store = TempDataStore(str(tmp_path))

    with TestClient(test_app) as client:
        job_id = upload(client).json()["job_id"]
        wait_for_status(client, job_id, "completed")
        result_response = client.get(f"/api/analyze/{job_id}/result")

    assert classifier.received_transcript == "검찰청을 사칭했습니다."
    assert result_response.json()["result"]["corrections"] == [
        {
            "rule_id": "domain-investigation-001",
            "from": "검찰 청",
            "to": "검찰청",
            "reason": "수사기관명 표기 교정",
        }
    ]


def test_analysis_pipeline_records_failure_and_cleans_up(tmp_path: Path):
    test_app = build_app(FailingTranscriber())
    test_app.state.temp_data_store = TempDataStore(str(tmp_path))

    with TestClient(test_app) as client:
        create_response = upload(client)

        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        status = wait_for_status(client, job_id, "failed")
        assert status == {
            "job_id": job_id,
            "status": "failed",
            "stage": "failed",
        }

        job = test_app.state.job_registry.get(job_id)
        assert job is not None
        assert job.error == {
            "error_code": "ANALYSIS.FAILED",
            "message": "분석 중 오류가 발생했습니다.",
        }
        assert list(tmp_path.iterdir()) == []
        assert test_app.state.task_registry.get(job_id) is None

        second_response = upload(client)
        assert second_response.status_code == 202


def test_result_endpoint_rejects_incomplete_job():
    test_app = build_app(FakeTranscriber())

    with TestClient(test_app) as client:
        job = test_app.state.job_registry.create(owner_key="test-owner")
        job_id = job.job_id

        result_response = client.get(f"/api/analyze/{job_id}/result")

        assert result_response.status_code == 409
        assert result_response.json()["error_code"] == "JOB.NOT_COMPLETED"
