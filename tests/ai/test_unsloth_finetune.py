"""
Unit tests for Unsloth.ai Fine-Tuning & Dataset Generator Module.
"""

import json
import os
import tempfile
import unittest

from src.ai.unsloth_finetune import BulgarianAccountingDatasetGenerator, UnslothFineTuner


class TestUnslothFineTune(unittest.TestCase):
    """Test suite for UnslothFineTuner and BulgarianAccountingDatasetGenerator."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.generator = BulgarianAccountingDatasetGenerator()
        self.finetuner = UnslothFineTuner()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_samples_schema(self):
        samples = self.generator.generate_samples(count=10)
        self.assertEqual(len(samples), 10)
        for s in samples:
            self.assertIn("instruction", s)
            self.assertIn("input", s)
            self.assertIn("output", s)
            self.assertIn("formatted_text", s)
            out_data = json.loads(s["output"])
            self.assertIn("debit_account", out_data)
            self.assertIn("credit_account", out_data)

    def test_export_dataset_jsonl(self):
        out_jsonl = os.path.join(self.temp_dir.name, "training_data.jsonl")
        res_path = self.generator.export_dataset_jsonl(out_jsonl, count=25)
        self.assertTrue(os.path.exists(res_path))

        lines = []
        with open(res_path, "r", encoding="utf-8") as f:
            for line in f:
                lines.append(json.loads(line))

        self.assertEqual(len(lines), 25)
        self.assertIn("instruction", lines[0])

    def test_get_training_config(self):
        cfg = self.finetuner.get_training_config()
        self.assertEqual(cfg["model_name"], "unsloth/Llama-3.2-3B-Instruct")
        self.assertEqual(cfg["lora_r"], 16)
        self.assertTrue(cfg["load_in_4bit"])


if __name__ == "__main__":
    unittest.main()
