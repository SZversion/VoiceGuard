import asyncio

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.analysis.audio_chunking import TranscriptChunk
from app.analysis.classifier import ClassifierOutput


class ChunkedTranscriber:
    async def transcribe_chunks(self, audio: bytes):
        return [
            TranscriptChunk(0.0, 30.0, "first"),
            TranscriptChunk(30.0, 60.0, "second"),
            TranscriptChunk(60.0, 90.0, "third"),
        ]


class Classifier:
    def classify(self, transcript: str) -> ClassifierOutput:
        scores = {"first": 0.1, "second": 0.9, "third": 0.7}
        score = scores[transcript]
        label = "voice_phishing" if score >= 0.5 else "normal"
        return ClassifierOutput(label, int(label == "voice_phishing"), score)


def test_analyzer_aggregates_top_five_and_returns_top_three_segments():
    analyzer = VoicePhishingAnalyzer(ChunkedTranscriber(), Classifier())

    result = asyncio.run(analyzer.analyze(b"audio"))

    assert result["label"] == "voice_phishing"
    assert result["suspicion_score"] == (0.9 + 0.7 + 0.1) / 3
    assert result["reference_segments"] == [
        {
            "start": 30.0,
            "end": 60.0,
            "transcript": "second",
            "suspicion_score": 0.9,
        },
        {
            "start": 60.0,
            "end": 90.0,
            "transcript": "third",
            "suspicion_score": 0.7,
        },
        {
            "start": 0.0,
            "end": 30.0,
            "transcript": "first",
            "suspicion_score": 0.1,
        },
    ]
