"""Shared loading, generation, and output helpers for Whisper LoRA runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.stt_metrics import MetricResult


def build_evaluation_summary(results: list[MetricResult], failures: list[dict[str, str]] | None = None) -> dict[str, Any]:
    failures = failures or []
    return {
        "count": len(results),
        "average_cer": sum(item.cer for item in results) / len(results) if results else None,
        "average_wer": sum(item.wer for item in results) / len(results) if results else None,
        "results": [
            {
                "audio": item.audio,
                "reference": item.reference,
                "hypothesis": item.hypothesis,
                "cer": item.cer,
                "wer": item.wer,
            }
            for item in results
        ],
        "failures": failures,
    }


def write_inference_result(
    output_root: Path,
    audio_name: str,
    transcript: str,
    segments: list[dict[str, Any]],
) -> Path:
    output = output_root / Path(audio_name).stem
    output.mkdir(parents=True, exist_ok=True)
    (output / "transcript.txt").write_text(transcript.strip() + "\n", encoding="utf-8")
    with (output / "segments.jsonl").open("w", encoding="utf-8") as handle:
        for segment in segments:
            handle.write(json.dumps(segment, ensure_ascii=False) + "\n")
    return output


def load_whisper_lora_checkpoint(
    checkpoint: Path, device: str = "cuda", base_model: Path | str | None = None
):
    try:
        import torch
        from peft import PeftConfig, PeftModel
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
    except ImportError as error:
        raise RuntimeError(
            "Transformers, PEFT, and PyTorch are required for Whisper LoRA inference. "
            "Install requirements.txt in the inference environment."
        ) from error

    peft_config = PeftConfig.from_pretrained(checkpoint)
    processor = WhisperProcessor.from_pretrained(checkpoint)
    base_model_name = base_model or peft_config.base_model_name_or_path
    base = WhisperForConditionalGeneration.from_pretrained(base_model_name, local_files_only=bool(base_model))
    model = PeftModel.from_pretrained(base, checkpoint, local_files_only=True)
    target_device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
    model.to(target_device)
    model.eval()
    return model, processor, target_device


def load_base_whisper_checkpoint(checkpoint: Path, device: str = "cuda"):
    try:
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
    except ImportError as error:
        raise RuntimeError("Transformers and PyTorch are required for Whisper inference.") from error

    processor = WhisperProcessor.from_pretrained(checkpoint, local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(checkpoint, local_files_only=True)
    target_device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
    model.to(target_device)
    model.eval()
    return model, processor, target_device


def load_audio_file(audio_path: Path):
    """Decode and resample common audio files without constructing an Arrow dataset."""
    try:
        import av
        import numpy as np
    except ImportError as error:
        raise RuntimeError("PyAV and NumPy are required to decode audio.") from error

    container = av.open(str(audio_path))
    stream = next((item for item in container.streams if item.type == "audio"), None)
    if stream is None:
        container.close()
        raise ValueError(f"No audio stream found: {audio_path}")

    resampler = av.audio.resampler.AudioResampler(format="fltp", layout="mono", rate=16000)
    chunks = []
    try:
        for frame in container.decode(stream):
            for converted in resampler.resample(frame):
                chunks.append(converted.to_ndarray().reshape(-1))
        for converted in resampler.resample(None):
            chunks.append(converted.to_ndarray().reshape(-1))
    finally:
        container.close()

    if not chunks:
        raise ValueError(f"Audio stream contains no samples: {audio_path}")
    return {"array": np.concatenate(chunks).astype("float32", copy=False), "sampling_rate": 16000}


def transcribe_audio(audio_path: Path, model, processor, device: str) -> tuple[str, list[dict[str, Any]]]:
    import torch

    audio = load_audio_file(audio_path)
    inputs = processor.feature_extractor(
        audio["array"], sampling_rate=audio["sampling_rate"], return_tensors="pt"
    )
    input_features = inputs.input_features.to(device)
    with torch.no_grad():
        generated = model.generate(input_features=input_features)
    text = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
    return text, [{"start": 0.0, "end": None, "text": text}]
