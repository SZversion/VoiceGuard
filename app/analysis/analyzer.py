from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

from app.analysis.classifier import TextClassifier
from app.analysis.domain_corrector import DomainTermCorrector
from app.analysis.transcript_quality import TranscriptQualityFilter


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
        corrector: DomainTermCorrector | None = None,
        quality_filter: TranscriptQualityFilter | None = None,
    ):
        self.transcriber = transcriber
        self.classifier = classifier
        self.guidance = guidance
        self.corrector = corrector or DomainTermCorrector([])
        self.quality_filter = quality_filter or TranscriptQualityFilter()

    async def analyze(self, audio: bytes) -> Mapping[str, object]:
        raw_transcript = await self._transcribe(audio)
        correction = self.corrector.correct(raw_transcript)
        quality = self.quality_filter.check(correction.corrected_transcript)
        if not quality.usable:
            return {
                "raw_transcript": correction.raw_transcript,
                "corrected_transcript": correction.corrected_transcript,
                "corrections": [
                    {
                        "rule_id": item.rule_id,
                        "from": item.source,
                        "to": item.target,
                        "reason": item.reason,
                    }
                    for item in correction.corrections
                ],
                "classification_status": "skipped",
                "quality": {
                    "usable": quality.usable,
                    "score": quality.score,
                    "reason": quality.reason,
                },
                "reference_segments": [],
                "guidance": self.guidance,
            }
        result = self.classifier.classify(correction.corrected_transcript)
        return {
            "raw_transcript": correction.raw_transcript,
            "corrected_transcript": correction.corrected_transcript,
            "corrections": [
                {
                    "rule_id": item.rule_id,
                    "from": item.source,
                    "to": item.target,
                    "reason": item.reason,
                }
                for item in correction.corrections
            ],
            "label": result.label,
            "suspicion_score": result.suspicion_score,
            "classification_status": "classified",
            "quality": {
                "usable": quality.usable,
                "score": quality.score,
                "reason": quality.reason,
            },
            "reference_segments": [],
            "guidance": self.guidance,
        }

    async def _transcribe(self, audio: bytes) -> str:
        if hasattr(self.transcriber, "transcribe"):
            return await self.transcriber.transcribe(audio)
        return await self.transcriber(audio)
