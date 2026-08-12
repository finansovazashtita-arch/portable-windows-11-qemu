"""
Unit tests for Active Learning Feedback Loop Module.
"""

import os
import tempfile
import unittest

from src.ai.active_learning_loop import ActiveLearningManager


class TestActiveLearningLoop(unittest.TestCase):
    """Test suite for ActiveLearningManager."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dataset_path = os.path.join(self.temp_dir.name, "al_dataset.jsonl")
        self.al_mgr = ActiveLearningManager(dataset_path=self.dataset_path, retrain_threshold=3)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_correction(self):
        fb = self.al_mgr.record_correction(
            narrative="ПЛАЩАНЕ НАЕМ НАЕМНО ПОМЕЩЕНИЕ",
            predicted_debit="401",
            predicted_credit="503",
            corrected_debit="602",
            corrected_credit="503",
            accountant_rationale="Наемни разходи",
        )

        self.assertEqual(fb.corrected_debit, "602")
        self.assertEqual(fb.corrected_credit, "503")
        self.assertTrue(os.path.exists(self.dataset_path))
        self.assertEqual(self.al_mgr.get_dataset_size(), 1)

    def test_retraining_trigger_threshold(self):
        self.assertFalse(self.al_mgr.check_and_trigger_retraining())

        self.al_mgr.record_correction("N1", "401", "503", "602", "503")
        self.al_mgr.record_correction("N2", "401", "503", "602", "503")
        self.al_mgr.record_correction("N3", "401", "503", "602", "503")

        self.assertEqual(self.al_mgr.get_dataset_size(), 3)
        self.assertTrue(self.al_mgr.check_and_trigger_retraining())


if __name__ == "__main__":
    unittest.main()
