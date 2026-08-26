import pytest
import asyncio

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.analysis.classifier import ClassifierOutput
from app.analysis.domain_corrector import DomainTermCorrector, load_default_domain_rules


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
        "label": "voice_phishing",
        "suspicion_score": 0.9,
        "reference_segments": [],
        "guidance": "검토가 필요한 경우 금융기관 공식 채널로 확인하세요.",
        "raw_transcript": "검찰을 사칭하여 송금을 요구합니다.",
        "corrected_transcript": "검찰을 사칭하여 송금을 요구합니다.",
        "corrections": [],
        "classification_status": "classified",
        "quality": {
            "usable": True,
            "score": 1.0,
            "reason": None,
            "excluded_chunk_count": 0,
        },
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


def test_analyzer_classifies_corrected_domain_transcript():
    class DomainTranscriber:
        async def transcribe(self, audio: bytes) -> str:
            return "계절로 송금 계좌를 확인해 주세요."

    class DomainClassifier:
        def classify(self, transcript: str) -> ClassifierOutput:
            assert transcript == "계좌로 송금 계좌를 확인해 주세요."
            return ClassifierOutput("normal", 0, 0.1)

    analyzer = VoicePhishingAnalyzer(
        DomainTranscriber(),
        DomainClassifier(),
        corrector=DomainTermCorrector(load_default_domain_rules()),
    )

    result = asyncio.run(analyzer.analyze(b"audio"))

    assert result["corrected_transcript"] == "계좌로 송금 계좌를 확인해 주세요."
    assert result["corrections"][0]["source"] == "계절"
