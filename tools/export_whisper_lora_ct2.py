"""Merge the configured LoRA and export a reusable CTranslate2 INT8 model."""

import argparse
import json
import os
import tempfile
from pathlib import Path

from app.analysis.whisper_lora_loader import (
    ADAPTER_MODEL,
    BASE_MODEL,
    load_whisper_lora_transcriber,
)


def export_model(output_dir, loader=load_whisper_lora_transcriber, converter_factory=None):
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if converter_factory is None:
        from ctranslate2.converters import TransformersConverter
        converter_factory = TransformersConverter
    # Staging remains on the same filesystem so final rename is atomic.
    with tempfile.TemporaryDirectory(prefix="whisper-convert-", dir=output.parent) as tmp:
        staging = Path(tmp)
        merged = staging / "merged"
        converted = staging / "converted"
        transcriber = loader(device="cpu")
        transcriber.model.save_pretrained(merged, safe_serialization=True)
        transcriber.processor.save_pretrained(merged)
        # WhisperProcessor uses the slow tokenizer in Transformers 4.44.2;
        # Faster-Whisper needs the standalone tokenizer.json artifact.
        if not (merged / "tokenizer.json").is_file():
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(merged), use_fast=True)
            tokenizer.save_pretrained(merged)
        manifest = {
            "base_model": os.getenv("STT_BASE_MODEL", BASE_MODEL),
            "adapter_model": os.getenv("STT_ADAPTER_MODEL", ADAPTER_MODEL),
            "base_revision": getattr(transcriber.model.config, "_commit_hash", None),
            "merged": True,
            "quantization": "int8",
        }
        del transcriber
        converter = converter_factory(
            str(merged), copy_files=["tokenizer.json", "preprocessor_config.json"]
        )
        converter.convert(str(converted), quantization="int8")
        if not (converted / "model.bin").is_file():
            raise RuntimeError("Conversion did not create model.bin")
        (converted / "voiceguard_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        converted.rename(output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(f"Converted merged INT8 model: {export_model(args.output_dir)}")


if __name__ == "__main__":
    main()
