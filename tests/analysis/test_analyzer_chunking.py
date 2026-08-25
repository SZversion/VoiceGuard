import asyncio

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.analysis.classifier import ClassifierOutput


class Transcriber:
    async def transcribe(self, audio: bytes) -> str:
        return "long transcript"


class ChunkClassifier:
    def classify_chunks(self, transcript: str):
        return [
            ("normal chunk", ClassifierOutput("normal", 0, 0.2)),
            ("fraud chunk", ClassifierOutput("voice_phishing", 1, 0.9)),
        ]


def test_analyzer_aggregates_chunk_results_with_or_policy():
    analyzer = VoicePhishingAnalyzer(Transcriber(), ChunkClassifier())

    result = asyncio.run(analyzer.analyze(b"audio"))

    assert result["label"] == "voice_phishing"
    assert result["suspicion_score"] == 0.9
