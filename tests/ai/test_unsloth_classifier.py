"""
Unit tests for Unsloth AI Classifier.
"""

import unittest
from src.ai.unsloth_classifier import UnslothTransactionClassifier


class TestUnslothTransactionClassifier(unittest.TestCase):
    """Test suite for UnslothTransactionClassifier."""

    def setUp(self):
        self.classifier = UnslothTransactionClassifier()

    def test_classify_bank_fee(self):
        dt, cr, label = self.classifier.classify_narrative("БАНКОВА ТАКСА ПРЕВОД", 2.50, 0.00)
        self.assertEqual(dt, "621")
        self.assertEqual(cr, "503")
        self.assertIn("Банкови такси", label)

    def test_classify_rent(self):
        dt, cr, label = self.classifier.classify_narrative("ПЛАЩАНЕ НАЕМ ЗА МЕСЕЦ ЯНУАРИ", 500.00, 0.00)
        self.assertEqual(dt, "602")
        self.assertEqual(cr, "503")
        self.assertIn("Наем", label)

    def test_classify_customer_receipt(self):
        dt, cr, label = self.classifier.classify_narrative("ПОСТЪПЛЕНИЕ ОТ КЛИЕНТ ФАКТУРА 123", 0.00, 1200.00)
        self.assertEqual(dt, "503")
        self.assertEqual(cr, "411")

    def test_batch_classify(self):
        txs = [
            {"narrative_description": "ТАКСА ОБСЛУЖВАНЕ", "debit_amount": 10.00, "credit_amount": 0.00},
            {"narrative_description": "ПЛАЩАНЕ ПО ФАКТУРА 99", "debit_amount": 250.00, "credit_amount": 0.00}
        ]
        enriched = self.classifier.batch_classify(txs)
        self.assertEqual(len(enriched), 2)
        self.assertEqual(enriched[0]["ai_debit_account"], "621")
        self.assertEqual(enriched[1]["ai_debit_account"], "401")


if __name__ == "__main__":
    unittest.main()
