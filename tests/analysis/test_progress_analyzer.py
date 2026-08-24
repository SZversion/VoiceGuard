import asyncio

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.analysis.classifier import ClassifierOutput


class FakeTranscriber:
    async def transcribe(self, audio: bytes) -> str:
        return "test transcript"


class FakeClassifier:
    def classify(self, transcript: str) -> ClassifierOutput:
        assert transcript == "test transcript"
        return ClassifierOutput("normal", 0, 0.1)


def test_analyzer_reports_logical_pipeline_boundaries():
    analyzer = VoicePhishingAnalyzer(FakeTranscriber(), FakeClassifier())
    stages = []

    asyncio.run(analyzer.analyze_with_progress(b"audio", stages.append))

    assert stages == [
        "transcribing",
        "normalizing",
        "classifying",
        "risk_search",
        "finalizing",
    ]
