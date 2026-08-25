from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

from app.analysis.audio_chunking import TranscriptChunk
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
        transcribe_chunks = getattr(self.transcriber, "transcribe_chunks", None)
        if transcribe_chunks is not None:
            return await self._analyze_audio_chunks(
                audio,
                report_stage,
                transcribe_chunks,
            )

        report_stage("transcribing")
        transcript = await self._transcribe(audio)
        return self._classify_single_transcript(transcript, report_stage)

    async def _analyze_audio_chunks(
        self,
        audio: bytes,
        report_stage: StageReporter,
        transcribe_chunks,
    ) -> Mapping[str, object]:
        report_stage("transcribing")
        transcript_chunks: list[TranscriptChunk] = await transcribe_chunks(audio)
        scored_chunks: list[tuple[TranscriptChunk, ClassifierOutput]] = []

        for transcript_chunk in transcript_chunks:
            report_stage("normalizing")
            normalized_transcript = normalize_finance_text(
                transcript_chunk.transcript
            )

            report_stage("classifying")
            result = self._classify_transcript(normalized_transcript)
            scored_chunks.append((transcript_chunk, result))

        if not scored_chunks:
            raise ValueError("audio chunk transcription returned no results")

        report_stage("risk_search")
        ranked_chunks = sorted(
            scored_chunks,
            key=lambda item: item[1].suspicion_score,
            reverse=True,
        )
        top_five = ranked_chunks[:5]
        aggregated_score = sum(
            result.suspicion_score for _, result in top_five
        ) / len(top_five)
        label = "voice_phishing" if aggregated_score >= 0.5 else "normal"

        report_stage("finalizing")
        return {
            "label": label,
            "suspicion_score": aggregated_score,
            "reference_segments": [
                {
                    "start": chunk.start,
                    "end": chunk.end,
                    "transcript": normalize_finance_text(chunk.transcript),
                    "suspicion_score": result.suspicion_score,
                }
                for chunk, result in ranked_chunks[:3]
            ],
            "guidance": self.guidance,
        }

    def _classify_single_transcript(
        self,
        transcript: str,
        report_stage: StageReporter,
    ) -> Mapping[str, object]:
        report_stage("normalizing")
        normalized_transcript = normalize_finance_text(transcript)

        report_stage("classifying")
        result = self._classify_transcript(normalized_transcript)

        report_stage("risk_search")
        reference_segments = []

        report_stage("finalizing")
        return {
            "label": result.label,
            "suspicion_score": result.suspicion_score,
            "reference_segments": reference_segments,
            "guidance": self.guidance,
        }

    def _classify_transcript(self, transcript: str) -> ClassifierOutput:
        classify_chunks = getattr(self.classifier, "classify_chunks", None)
        if classify_chunks is None:
            return self.classifier.classify(transcript)

        chunk_results = classify_chunks(transcript)
        return self._aggregate_chunk_results(chunk_results)

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
