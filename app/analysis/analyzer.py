import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

from app.analysis.audio_chunking import TranscriptChunk
from app.analysis.classifier import ClassifierOutput, TextClassifier
from app.analysis.domain_corrector import DomainTermCorrector
from app.analysis.text_normalizer import normalize_finance_text
from app.analysis.transcript_quality import TranscriptQualityFilter


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes) -> str:
        ...


StageReporter = Callable[[str], None]


logger = logging.getLogger(__name__)


class VoicePhishingAnalyzer:
    """Run transcription and text classification as one analyzer."""

    def __init__(
        self,
        transcriber: Transcriber | Callable[[bytes], Awaitable[str]],
        classifier: TextClassifier,
        guidance: str = "\uac80\ud1a0\uac00 \ud544\uc694\ud55c \uacbd\uc6b0 \uae08\uc735\uae30\uad00 \uacf5\uc2dd \ucc44\ub110\ub85c \ud655\uc778\ud558\uc138\uc694.",
        corrector: DomainTermCorrector | None = None,
        quality_filter: TranscriptQualityFilter | None = None,
    ):
        self.transcriber = transcriber
        self.classifier = classifier
        self.guidance = guidance
        self.corrector = corrector or DomainTermCorrector([])
        self.quality_filter = quality_filter or TranscriptQualityFilter()

    async def analyze(self, audio: bytes) -> Mapping[str, object]:
        return await self.analyze_with_progress(audio, lambda stage: None)

    async def analyze_with_progress(
        self,
        audio: bytes,
        report_stage: StageReporter,
        report_progress: Callable[[dict[str, int | str]], None] | None = None,
    ) -> Mapping[str, object]:
        transcribe_stream = getattr(self.transcriber, "transcribe_chunks_stream", None)
        if transcribe_stream is not None:
            return await self._analyze_streaming_chunks(
                audio, report_stage, transcribe_stream, report_progress
            )

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

    async def _analyze_streaming_chunks(
        self,
        audio: bytes,
        report_stage: StageReporter,
        transcribe_stream,
        report_progress: Callable[[dict[str, int | str]], None] | None,
    ) -> Mapping[str, object]:
        report_stage("transcribing")
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        sentinel = object()
        scored_chunks: list[tuple[TranscriptChunk, str, ClassifierOutput]] = []
        prepared_chunks: list[tuple[TranscriptChunk, str, object, object]] = []

        async def produce() -> None:
            async for item in transcribe_stream(audio):
                await queue.put(item)
            await queue.put(sentinel)

        async def consume() -> None:
            transcribed = 0
            normalized = 0
            classified = 0
            total = 0
            while True:
                item = await queue.get()
                if item is sentinel:
                    break
                index, total, transcript_chunk = item
                transcribed = index
                logger.info("[transcribing] chunk %s/%s completed", index, total)
                if report_progress is not None:
                    report_progress({
                        "stage": "transcribing",
                        "transcribed_chunks": transcribed,
                        "normalized_chunks": normalized,
                        "classified_chunks": classified,
                        "total_chunks": total,
                    })
                normalized_transcript = normalize_finance_text(
                    transcript_chunk.transcript
                )
                normalized += 1
                if report_progress is not None:
                    report_progress({
                        "stage": "normalizing",
                        "transcribed_chunks": transcribed,
                        "normalized_chunks": normalized,
                        "classified_chunks": classified,
                        "total_chunks": total,
                    })
                correction = self.corrector.correct(normalized_transcript)
                quality = self.quality_filter.check(correction.corrected_transcript)
                prepared_chunks.append(
                    (transcript_chunk, correction.corrected_transcript, correction, quality)
                )
                if not quality.usable:
                    logger.info(
                        "[classifying] chunk %s/%s skipped quality=%s",
                        index,
                        total,
                        quality.reason,
                    )
                    continue

                logger.info("[classifying] chunk %s/%s started", index, total)
                started_at = time.perf_counter()
                result = await asyncio.to_thread(
                    self._classify_transcript,
                    correction.corrected_transcript,
                )
                logger.info(
                    "[classifying] chunk %s/%s completed latency_ms=%d",
                    index,
                    total,
                    round((time.perf_counter() - started_at) * 1000),
                )
                classified += 1
                scored_chunks.append((transcript_chunk, correction.corrected_transcript, result))
                if report_progress is not None:
                    report_progress({
                        "stage": "classifying",
                        "transcribed_chunks": transcribed,
                        "normalized_chunks": normalized,
                        "classified_chunks": classified,
                        "total_chunks": total,
                    })

        producer_task = asyncio.create_task(produce())
        consumer_task = asyncio.create_task(consume())
        try:
            await asyncio.gather(producer_task, consumer_task)
        finally:
            for task in (producer_task, consumer_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(
                producer_task,
                consumer_task,
                return_exceptions=True,
            )
        if not prepared_chunks:
            raise ValueError("audio chunk transcription returned no results")
        if not scored_chunks:
            return self._skipped_result(prepared_chunks)

        report_stage("risk_search")
        ranked_chunks = sorted(
            scored_chunks,
            key=lambda item: item[2].suspicion_score,
            reverse=True,
        )
        top_five = ranked_chunks[:5]
        aggregated_score = sum(
            result.suspicion_score for _, _, result in top_five
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
                    "transcript": corrected_transcript,
                    "suspicion_score": result.suspicion_score,
                }
                for chunk, corrected_transcript, result in ranked_chunks[:3]
            ],
            "guidance": self.guidance,
            **self._transcript_metadata(prepared_chunks),
        }
    async def _analyze_audio_chunks(
        self,
        audio: bytes,
        report_stage: StageReporter,
        transcribe_chunks,
    ) -> Mapping[str, object]:
        report_stage("transcribing")
        transcript_chunks: list[TranscriptChunk] = await transcribe_chunks(audio)
        scored_chunks: list[tuple[TranscriptChunk, str, ClassifierOutput]] = []
        prepared_chunks: list[tuple[TranscriptChunk, str, object, object]] = []

        for transcript_chunk in transcript_chunks:
            report_stage("normalizing")
            normalized_transcript = normalize_finance_text(
                transcript_chunk.transcript
            )

            correction = self.corrector.correct(normalized_transcript)
            quality = self.quality_filter.check(correction.corrected_transcript)
            prepared_chunks.append(
                (transcript_chunk, correction.corrected_transcript, correction, quality)
            )
            if not quality.usable:
                continue
            report_stage("classifying")
            result = self._classify_transcript(correction.corrected_transcript)
            scored_chunks.append((transcript_chunk, correction.corrected_transcript, result))

        if not prepared_chunks:
            raise ValueError("audio chunk transcription returned no results")
        if not scored_chunks:
            return self._skipped_result(prepared_chunks)

        report_stage("risk_search")
        ranked_chunks = sorted(
            scored_chunks,
            key=lambda item: item[2].suspicion_score,
            reverse=True,
        )
        top_five = ranked_chunks[:5]
        aggregated_score = sum(
            result.suspicion_score for _, _, result in top_five
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
                    "transcript": corrected_transcript,
                    "suspicion_score": result.suspicion_score,
                }
                for chunk, corrected_transcript, result in ranked_chunks[:3]
            ],
            "guidance": self.guidance,
            **self._transcript_metadata(prepared_chunks),
        }

    def _classify_single_transcript(
        self,
        transcript: str,
        report_stage: StageReporter,
    ) -> Mapping[str, object]:
        report_stage("normalizing")
        normalized_transcript = normalize_finance_text(transcript)
        correction = self.corrector.correct(normalized_transcript)
        quality = self.quality_filter.check(correction.corrected_transcript)

        if not quality.usable:
            report_stage("risk_search")
            report_stage("finalizing")
            return {
                "raw_transcript": normalized_transcript,
                "corrected_transcript": correction.corrected_transcript,
                "corrections": self._serialize_corrections(correction),
                "classification_status": "skipped",
                "quality": {
                    "usable": quality.usable,
                    "score": quality.score,
                    "reason": quality.reason,
                    "excluded_chunk_count": 1,
                },
                "reference_segments": [],
                "guidance": self.guidance,
            }

        report_stage("classifying")
        result = self._classify_transcript(correction.corrected_transcript)

        report_stage("risk_search")
        reference_segments = []

        report_stage("finalizing")
        return {
            "label": result.label,
            "suspicion_score": result.suspicion_score,
            "reference_segments": reference_segments,
            "guidance": self.guidance,
            "raw_transcript": normalized_transcript,
            "corrected_transcript": correction.corrected_transcript,
            "corrections": self._serialize_corrections(correction),
            "classification_status": "classified",
            "quality": {
                "usable": quality.usable,
                "score": quality.score,
                "reason": quality.reason,
                "excluded_chunk_count": 0,
            },
        }

    @staticmethod
    def _serialize_corrections(correction) -> list[dict[str, str]]:
        return [
            {
                "rule_id": item.rule_id,
                "source": item.source,
                "target": item.target,
                "reason": item.reason,
                "kind": item.kind,
            }
            for item in correction.corrections
        ]

    def _transcript_metadata(self, prepared_chunks) -> dict[str, object]:
        raw_transcript = " ".join(chunk.transcript for chunk, _, _, _ in prepared_chunks)
        corrected_transcript = " ".join(
            corrected for _, corrected, _, _ in prepared_chunks
        )
        quality_results = [quality for _, _, _, quality in prepared_chunks]
        excluded_count = sum(not quality.usable for quality in quality_results)
        score = round(
            sum(quality.score for quality in quality_results) / len(quality_results),
            4,
        ) if quality_results else 0.0
        corrections = [
            correction
            for _, _, item, _ in prepared_chunks
            for correction in self._serialize_corrections(item)
        ]
        return {
            "raw_transcript": raw_transcript,
            "corrected_transcript": corrected_transcript,
            "corrections": corrections,
            "classification_status": "classified",
            "quality": {
                "usable": excluded_count == 0,
                "score": score,
                "reason": None if excluded_count == 0 else "some_chunks_unusable",
                "excluded_chunk_count": excluded_count,
            },
        }

    def _skipped_result(self, prepared_chunks) -> Mapping[str, object]:
        metadata = self._transcript_metadata(prepared_chunks)
        metadata["classification_status"] = "skipped"
        quality = metadata["quality"]
        quality["reason"] = "all_chunks_unusable"
        return {
            **metadata,
            "reference_segments": [],
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
