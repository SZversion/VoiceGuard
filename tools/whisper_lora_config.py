"""Configuration loading and validation for Whisper LoRA workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_TOP_LEVEL_KEYS = {"data", "model_name", "language", "task", "lora", "training"}


def load_whisper_lora_config(path: Path) -> dict[str, Any]:
    """Load a Whisper LoRA YAML config and validate its public contract."""
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if not isinstance(config, dict):
        raise ValueError("Whisper LoRA config must be a YAML mapping")

    missing = REQUIRED_TOP_LEVEL_KEYS - set(config)
    if missing:
        raise ValueError(f"Whisper LoRA config is missing keys: {sorted(missing)}")

    if config["language"] != "ko":
        raise ValueError("This workflow currently requires language=ko")

    lora = config["lora"]
    if lora.get("target_modules") != ["q_proj", "v_proj"]:
        raise ValueError("LoRA target_modules must be [q_proj, v_proj]")

    data = config["data"]
    ratios = [data.get("train_ratio"), data.get("validation_ratio"), data.get("test_ratio")]
    if any(not isinstance(value, (int, float)) or value <= 0 for value in ratios):
        raise ValueError("data split ratios must be positive numbers")
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError("data split ratios must sum to 1.0")

    return config
