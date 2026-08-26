import pytest
import asyncio

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.analysis.classifier import ClassifierOutput
from app.analysis.domain_corrector import (
    AppliedCorrection,
    DomainCorrectionResult,
)


class FakeTranscriber:
    async def transcribe(self, audio: bytes) -> str:
        assert audio == b"audio"
        return "검찰을 사칭하여 송금을 요구합니다."


class FakeClassifier:
    def classify(self, transcript: str) -> ClassifierOutput:
        assert transcript == "검찰을 사칭하여 송금을 요구합니다."
        return ClassifierOutput(
            label="voice_phishing",
            label_id=1,
            suspicion_score=0.9,
        )



def test_analyzer_connects_transcription_to_classification():
    analyzer = VoicePhishingAnalyzer(FakeTranscriber(), FakeClassifier())

    result = asyncio.run(analyzer.analyze(b"audio"))

    assert result == {
        "raw_transcript": "검찰을 사칭하여 송금을 요구합니다.",
        "corrected_transcript": "검찰을 사칭하여 송금을 요구합니다.",
        "corrections": [],
        "label": "voice_phishing",
        "suspicion_score": 0.9,
        "classification_status": "classified",
        "quality": {"usable": True, "score": 1.0, "reason": None},
        "reference_segments": [],
        "guidance": "검토가 필요한 경우 금융기관 공식 채널로 확인하세요.",
    }



def test_analyzer_propagates_empty_transcript_failure():
    class EmptyTranscriber:
        async def transcribe(self, audio: bytes) -> str:
            return ""

    class FailingClassifier:
        def classify(self, transcript: str):
            raise ValueError("transcript must not be empty")

    analyzer = VoicePhishingAnalyzer(EmptyTranscriber(), FailingClassifier())

    with pytest.raises(ValueError, match="transcript"):
        asyncio.run(analyzer.analyze(b"audio"))


def test_analyzer_classifies_corrected_transcript_and_returns_both_versions():
    class FakeCorrector:
        def correct(self, transcript: str) -> DomainCorrectionResult:
            return DomainCorrectionResult(
                raw_transcript=transcript,
                corrected_transcript="검찰청을 사칭하여 송금을 요구합니다.",
                corrections=(
                    AppliedCorrection("r1", "검찰 청", "검찰청", "기관명"),
                ),
            )

    class RecordingClassifier:
        def classify(self, transcript: str) -> ClassifierOutput:
            assert transcript == "검찰청을 사칭하여 송금을 요구합니다."
            return ClassifierOutput("voice_phishing", 1, 0.9)

    analyzer = VoicePhishingAnalyzer(
        FakeTranscriber(),
        RecordingClassifier(),
        corrector=FakeCorrector(),
    )

    result = asyncio.run(analyzer.analyze(b"audio"))

    assert result["raw_transcript"] == "검찰을 사칭하여 송금을 요구합니다."
    assert result["corrected_transcript"] == "검찰청을 사칭하여 송금을 요구합니다."
    assert result["corrections"] == [
        {
            "rule_id": "r1",
            "from": "검찰 청",
            "to": "검찰청",
            "reason": "기관명",
        }
    ]


def test_analyzer_skips_classifier_for_unusable_transcript():
    class BrokenTranscriber:
        async def transcribe(self, audio: bytes) -> str:
            return "아아 아아 아아 아아 아아"

    class FailingClassifier:
        def classify(self, transcript: str):
            raise AssertionError("classifier must not be called")

    analyzer = VoicePhishingAnalyzer(BrokenTranscriber(), FailingClassifier())

    result = asyncio.run(analyzer.analyze(b"audio"))

    assert result["classification_status"] == "skipped"
    assert result["quality"]["reason"] == "repeated_tokens"
    assert result["raw_transcript"] == "아아 아아 아아 아아 아아"
    assert result["corrected_transcript"] == "아아 아아 아아 아아 아아"
