import json
import unittest
from pathlib import Path


class WhisperLoraNotebookTests(unittest.TestCase):
    def test_whisper_lora_notebooks_are_valid_json_and_have_required_sections(self):
        paths = list(Path("notebooks").glob("whisper_lora_*.ipynb"))
        self.assertEqual(len(paths), 3)
        for path in paths:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
            self.assertNotIn('HF_TOKEN = "hf_', source)
            if path.name == "whisper_lora_inference.ipynb":
                self.assertIn("load_whisper_lora_checkpoint", source)
                self.assertIn("transcribe_audio", source)
                self.assertIn("run-002", source)
            else:
                self.assertTrue("CER" in source or "WER" in source)


if __name__ == "__main__":
    unittest.main()
