import asyncio

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.analysis.classifier import ClassifierOutput


class Transcriber:
    async def transcribe(self, audio: bytes) -> str:
        return "\ud53c\ud574\uc790: \uac80\ucc30 + \uc0ac\uce6d"


class Classifier:
    def classify(self, transcript: str) -> ClassifierOutput:
        assert transcript == "\uac80\ucc30 \uc0ac\uce6d"
        return ClassifierOutput("voice_phishing", 1, 0.9)


def test_analyzer_classifies_normalized_transcript():
    analyzer = VoicePhishingAnalyzer(Transcriber(), Classifier())

    result = asyncio.run(analyzer.analyze(b"audio"))

    assert result["label"] == "voice_phishing"
