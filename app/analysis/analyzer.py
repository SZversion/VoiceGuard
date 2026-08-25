from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

from app.analysis.classifier import ClassifierOutput, TextClassifier
from app.analysis.text_normalizer import normalize_finance_text


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes) -> str:
        ...


StageReporter = Callable[[str], None]


class VoicePhishingAnalyzer:
    """Run transcription and text classification as one analyzer."""

    def __init__(
        self,
        transcriber: Transcriber | Callable[[bytes], Awaitable[str]],
        classifier: TextClassifier,
        guidance: str = "\uac80\ud1a0\uac00 \ud544\uc694\ud55c \uacbd\uc6b0 \uae08\uc735\uae30\uad00 \uacf5\uc2dd \ucc44\ub110\ub85c \ud655\uc778\ud558\uc138\uc694.",
    ):
        self.transcriber = transcriber
        self.classifier = classifier
        self.guidance = guidance

    async def analyze(self, audio: bytes) -> Mapping[str, object]:
        return await self.analyze_with_progress(audio, lambda stage: None)

    async def analyze_with_progress(
        self,
        audio: bytes,
        report_stage: StageReporter,
    ) -> Mapping[str, object]:
        report_stage("transcribing")
        transcript = await self._transcribe(audio)

        report_stage("normalizing")
        normalized_transcript = normalize_finance_text(transcript)

        report_stage("classifying")
        classify_chunks = getattr(self.classifier, "classify_chunks", None)
        if classify_chunks is None:
            result = self.classifier.classify(normalized_transcript)
        else:
            chunk_results = classify_chunks(normalized_transcript)
            result = self._aggregate_chunk_results(chunk_results)

        report_stage("risk_search")
        reference_segments = []

        report_stage("finalizing")
        return {
            "label": result.label,
            "suspicion_score": result.suspicion_score,
            "reference_segments": reference_segments,
            "guidance": self.guidance,
        }

    @staticmethod
    def _aggregate_chunk_results(
        chunk_results: list[tuple[str, ClassifierOutput]],
    ) -> ClassifierOutput:
        if not chunk_results:
            raise ValueError("chunk classification returned no results")

        suspicion_score = max(result.suspicion_score for _, result in chunk_results)
        is_voice_phishing = any(
            result.label == "voice_phishing" for _, result in chunk_results
        )
        return ClassifierOutput(
            label="voice_phishing" if is_voice_phishing else "normal",
            label_id=1 if is_voice_phishing else 0,
            suspicion_score=suspicion_score,
        )

    async def _transcribe(self, audio: bytes) -> str:
        if hasattr(self.transcriber, "transcribe"):
            return await self.transcriber.transcribe(audio)
        return await self.transcriber(audio)
