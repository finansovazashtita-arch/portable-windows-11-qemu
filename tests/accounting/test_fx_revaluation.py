"""
Unit tests for Multi-Currency FX Revaluation Engine.
"""

import unittest

from src.accounting.fx_revaluation import FXRateProvider, FXRevaluationCalculator


class TestFXRevaluation(unittest.TestCase):
    """Test suite for FXRevaluationCalculator and FXRateProvider."""

    def test_fixed_rate_peg_bgn(self):
        rate = FXRateProvider.get_exchange_rate("BGN")
        self.assertAlmostEqual(rate, 1.0 / 1.95583, places=5)

    def test_fx_gain_calculation(self):
        # USD rate increased from 0.88 to 0.92 -> FX Gain
        res = FXRevaluationCalculator.calculate_revaluation(
            original_amount=1000.0,
            currency="USD",
            book_rate=0.88,
            current_rate=0.92,
        )
        self.assertEqual(res.fx_account_code, "724")
        self.assertEqual(res.fx_diff_eur, 40.0)

    def test_fx_loss_calculation(self):
        # USD rate decreased from 0.95 to 0.90 -> FX Loss
        res = FXRevaluationCalculator.calculate_revaluation(
            original_amount=1000.0,
            currency="USD",
            book_rate=0.95,
            current_rate=0.90,
        )
        self.assertEqual(res.fx_account_code, "624")
        self.assertEqual(res.fx_diff_eur, 50.0)

    def test_generate_fx_journal_entries(self):
        txs = [
            {"item_id": 1, "currency": "EUR", "debit_amount": 100.0},
            {"item_id": 2, "currency": "USD", "debit_amount": 1000.0, "book_rate": 0.88},
        ]
        entries = FXRevaluationCalculator.generate_fx_journal_entries(txs)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["debit_account"], "503")
        self.assertEqual(entries[0]["credit_account"], "724")


if __name__ == "__main__":
    unittest.main()
