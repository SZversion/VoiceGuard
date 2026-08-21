from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

from app.analysis.classifier import TextClassifier


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes) -> str:
        ...


class VoicePhishingAnalyzer:
    """Run transcription and text classification as one analyzer."""

    def __init__(
        self,
        transcriber: Transcriber | Callable[[bytes], Awaitable[str]],
        classifier: TextClassifier,
        guidance: str = "검토가 필요한 경우 금융기관 공식 채널로 확인하세요.",
    ):
        self.transcriber = transcriber
        self.classifier = classifier
        self.guidance = guidance

    async def analyze(self, audio: bytes) -> Mapping[str, object]:
        transcript = await self._transcribe(audio)
        result = self.classifier.classify(transcript)
        return {
            "label": result.label,
            "suspicion_score": result.suspicion_score,
            "reference_segments": [],
            "guidance": self.guidance,
        }

    async def _transcribe(self, audio: bytes) -> str:
        if hasattr(self.transcriber, "transcribe"):
            return await self.transcriber.transcribe(audio)
        return await self.transcriber(audio)
