import asyncio

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.analysis.audio_chunking import TranscriptChunk
from app.analysis.classifier import ClassifierOutput


class StreamingTranscriber:
    async def transcribe_chunks_stream(self, audio: bytes):
        for index, text in enumerate(("first", "second", "third"), start=1):
            yield index, 3, TranscriptChunk((index - 1) * 30.0, index * 30.0, text)
            await asyncio.sleep(0)


class StreamingClassifier:
    def classify(self, transcript: str) -> ClassifierOutput:
        score = {"first": 0.1, "second": 0.9, "third": 0.7}[transcript]
        label = "voice_phishing" if score >= 0.5 else "normal"
        return ClassifierOutput(label, int(label == "voice_phishing"), score)


class FailingStreamingTranscriber:
    async def transcribe_chunks_stream(self, audio: bytes):
        yield 1, 3, TranscriptChunk(0.0, 30.0, "first")
        raise RuntimeError("transcription failed")


def test_analyzer_streams_chunks_and_reports_classified_counts():
    progress = []
    analyzer = VoicePhishingAnalyzer(StreamingTranscriber(), StreamingClassifier())

    result = asyncio.run(
        analyzer.analyze_with_progress(
            b"audio",
            lambda stage: None,
            progress.append,
        )
    )

    assert result["label"] == "voice_phishing"
    assert progress[-1] == {
        "stage": "classifying",
        "transcribed_chunks": 3,
        "normalized_chunks": 3,
        "classified_chunks": 3,
        "total_chunks": 3,
    }

def test_streaming_pipeline_does_not_leave_consumer_task_pending_on_producer_error():
    analyzer = VoicePhishingAnalyzer(
        FailingStreamingTranscriber(),
        StreamingClassifier(),
    )

    try:
        asyncio.run(analyzer.analyze_with_progress(b"audio", lambda stage: None))
    except RuntimeError as exc:
        assert str(exc) == "transcription failed"
    else:
        raise AssertionError("expected the producer error")