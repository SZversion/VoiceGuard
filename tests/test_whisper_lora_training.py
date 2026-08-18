import importlib.util
import unittest

from tools.train_whisper_lora import build_lora_config, build_parser


class WhisperLoraTrainingTests(unittest.TestCase):
    def test_training_parser_supports_dry_run(self):
        args = build_parser().parse_args(["--data", "data/fine_tuning", "--output", "models/test", "--dry-run"])
        self.assertTrue(args.dry_run)

    @unittest.skipUnless(importlib.util.find_spec("peft"), "PEFT is not installed")
    def test_lora_config_targets_query_and_value_projections(self):
        config = build_lora_config({"r": 8, "alpha": 16, "dropout": 0.05, "target_modules": ["q_proj", "v_proj"]})
        self.assertEqual(set(config.target_modules), {"q_proj", "v_proj"})
        self.assertEqual(config.r, 8)

    @unittest.skipUnless(
        importlib.util.find_spec("peft") and importlib.util.find_spec("transformers"),
        "optional Whisper training dependencies are not installed",
    )
    def test_lora_target_modules_are_applied_to_whisper_model(self):
        self.skipTest("model download is intentionally not part of the unit test suite")


if __name__ == "__main__":
    unittest.main()
