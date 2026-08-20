"""Train a Hugging Face Whisper checkpoint with a PEFT LoRA adapter."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from tools.whisper_lora_config import load_whisper_lora_config
from tools.whisper_lora_data import SplitRatios, discover_pairs, split_pairs, split_pairs_by_source, write_manifest
from tools.whisper_lora_inference import load_audio_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fine-tune Whisper with LoRA on sibling audio/TXT pairs")
    parser.add_argument("--data", type=Path, required=True, help="directory containing audio/TXT pairs")
    parser.add_argument("--output", type=Path, required=True, help="run output directory")
    parser.add_argument("--config", type=Path, default=Path("configs/whisper_lora.yaml"))
    parser.add_argument("--model")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--resume-from-checkpoint")
    parser.add_argument("--fp16", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def build_lora_config(lora: dict[str, Any]):
    try:
        from peft import LoraConfig
    except ImportError as error:
        raise RuntimeError("PEFT is required for Whisper LoRA training. Install requirements.txt first.") from error

    return LoraConfig(
        r=int(lora["r"]),
        lora_alpha=int(lora["alpha"]),
        lora_dropout=float(lora["dropout"]),
        target_modules=list(lora["target_modules"]),
        bias="none",
        # Whisper's speech encoder consumes input_features rather than input_ids.
        # Leaving task_type unset makes PEFT use the generic PeftModel forward,
        # which preserves Whisper's speech-specific keyword arguments.
        task_type=None,
    )


def build_whisper_model(model_name: str, lora: dict[str, Any], language: str = "ko", task: str = "transcribe"):
    try:
        from peft import get_peft_model
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
    except ImportError as error:
        raise RuntimeError("Transformers and PEFT are required for Whisper LoRA training.") from error

    processor = WhisperProcessor.from_pretrained(model_name, language=language, task=task)
    model = WhisperForConditionalGeneration.from_pretrained(model_name)
    model.generation_config.language = language
    model.generation_config.task = task
    model.generation_config.forced_decoder_ids = None
    model.config.use_cache = False
    model = get_peft_model(model, build_lora_config(lora))
    model.print_trainable_parameters()
    return model, processor


def prepare_features(example: dict[str, Any], processor):
    audio = example["audio"]
    features = processor.feature_extractor(
        audio["array"],
        sampling_rate=audio["sampling_rate"],
    ).input_features[0]
    labels = processor.tokenizer(example["transcript"]).input_ids
    return {"input_features": features, "labels": labels}


class WhisperPairDataset:
    """Lazy torch dataset that avoids Arrow fingerprinting for very large corpora."""

    def __init__(self, pairs, processor):
        self.pairs = pairs
        self.processor = processor

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, index):
        pair = self.pairs[index]
        audio = load_audio_file(pair.audio)
        return prepare_features({"audio": audio, "transcript": pair.transcript}, self.processor)


class WhisperDataCollator:
    def __init__(self, processor):
        self.processor = processor

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        import torch

        input_features = [{"input_features": item["input_features"]} for item in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
        label_features = [{"input_ids": item["labels"]} for item in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch


def _load_training_dependencies():
    try:
        from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments
    except ImportError as error:
        raise RuntimeError(
            "Whisper LoRA training requires datasets, transformers, peft, and accelerate. "
            "Install requirements.txt in the training environment."
        ) from error
    return Seq2SeqTrainer, Seq2SeqTrainingArguments


def _build_training_arguments(training: dict[str, Any], output: Path, fp16: bool):
    _, Seq2SeqTrainingArguments = _load_training_dependencies()
    values = {
        "output_dir": str(output),
        "per_device_train_batch_size": int(training["per_device_train_batch_size"]),
        "per_device_eval_batch_size": int(training["per_device_eval_batch_size"]),
        "gradient_accumulation_steps": int(training["gradient_accumulation_steps"]),
        "learning_rate": float(training["learning_rate"]),
        "num_train_epochs": float(training["num_train_epochs"]),
        "fp16": fp16,
        "logging_steps": int(training.get("logging_steps", 10)),
        "save_total_limit": 2,
        "predict_with_generate": True,
        "remove_unused_columns": False,
        "report_to": [],
    }
    try:
        return Seq2SeqTrainingArguments(
            **values,
            eval_strategy=training.get("evaluation_strategy", "epoch"),
            save_strategy=training.get("save_strategy", "epoch"),
        )
    except TypeError:
        return Seq2SeqTrainingArguments(
            **values,
            evaluation_strategy=training.get("evaluation_strategy", "epoch"),
            save_strategy=training.get("save_strategy", "epoch"),
        )


def _prepare_manifest(data_root: Path, output: Path, config: dict[str, Any], seed: int) -> tuple[dict[str, list], list]:
    extensions = tuple(config["data"]["extensions"])
    pairs, issues = discover_pairs(
        data_root,
        extensions,
        clean_transcripts=bool(config["data"].get("clean_transcripts", False)),
        min_transcript_chars=int(config["data"].get("min_transcript_chars", 1)),
    )
    if len(pairs) < 3:
        raise ValueError(f"At least 3 valid audio/TXT pairs are required; found {len(pairs)}")
    ratios = SplitRatios(
        float(config["data"]["train_ratio"]),
        float(config["data"]["validation_ratio"]),
        float(config["data"]["test_ratio"]),
    )
    splitter = split_pairs_by_source if config["data"].get("group_by_source", False) else split_pairs
    splits = splitter(pairs, ratios, seed)
    write_manifest(splits, output / "dataset_manifest.jsonl")
    if issues:
        (output / "dataset_issues.json").write_text(
            json.dumps(
                [{"code": item.code, "path": str(item.path), "message": item.message} for item in issues],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return splits, issues


def train(args: argparse.Namespace) -> int:
    config = load_whisper_lora_config(args.config)
    args.output.mkdir(parents=True, exist_ok=True)
    model_name = args.model or config["model_name"]
    seed = args.seed if args.seed is not None else int(config["data"]["seed"])
    splits, issues = _prepare_manifest(args.data, args.output, config, seed)
    print(
        json.dumps(
            {
                "model": model_name,
                "counts": {key: len(value) for key, value in splits.items()},
                "issues": len(issues),
                "output": str(args.output),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if args.dry_run:
        print("[DRY-RUN] dataset validation and split completed; model training skipped", flush=True)
        return 0

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for training. Use --dry-run on CPU or install CUDA PyTorch.")
    fp16 = torch.cuda.is_available() if args.fp16 is None else args.fp16
    if fp16 and not torch.cuda.is_available():
        raise ValueError("--fp16 requires CUDA")

    Seq2SeqTrainer, _ = _load_training_dependencies()
    model, processor = build_whisper_model(model_name, config["lora"], config["language"], config["task"])
    datasets = {split: WhisperPairDataset(pairs, processor) for split, pairs in splits.items()}

    training_args = _build_training_arguments(config["training"], args.output, fp16)

    def compute_metrics(prediction):
        from tools.stt_metrics import cer, normalize_for_metric, wer

        predictions = prediction.predictions[0] if isinstance(prediction.predictions, tuple) else prediction.predictions
        labels = prediction.label_ids
        labels = labels.copy()
        labels[labels == -100] = processor.tokenizer.pad_token_id
        hypotheses = processor.batch_decode(predictions, skip_special_tokens=True)
        references = processor.batch_decode(labels, skip_special_tokens=True)
        return {
            "cer": sum(cer(ref, hyp) for ref, hyp in zip(references, hypotheses)) / len(references),
            "wer": sum(wer(ref, hyp) for ref, hyp in zip(references, hypotheses)) / len(references),
        }

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=datasets["train"],
        eval_dataset=datasets["validation"],
        data_collator=WhisperDataCollator(processor),
        compute_metrics=compute_metrics,
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(args.output)
    processor.save_pretrained(args.output)
    (args.output / "training_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return train(args)


if __name__ == "__main__":
    raise SystemExit(main())
