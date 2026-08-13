"""
Unit tests for Autonomous AI Synthetic Dataset Generator & Stress Harness Engine.
"""

import unittest

from src.ai.synthetic_stress_harness import SyntheticStressHarness


class TestSyntheticStressHarness(unittest.TestCase):
    """Test suite for SyntheticStressHarness."""

    def test_generate_synthetic_transactions(self):
        txs = SyntheticStressHarness.generate_synthetic_transactions(count=50)
        self.assertEqual(len(txs), 50)
        self.assertTrue(txs[0].tx_id.startswith("SYN_TX_"))
        self.assertGreater(txs[0].amount, 0)

    def test_run_stress_benchmark(self):
        res = SyntheticStressHarness.run_stress_benchmark(count=1000)
        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["total_transactions"], 1000)
        self.assertGreater(res["throughput_tx_per_sec"], 0)


if __name__ == "__main__":
    unittest.main()
