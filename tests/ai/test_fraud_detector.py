"""
Unit tests for AI Fraud Prevention & Anomaly Detection Engine.
"""

import unittest

from src.ai.fraud_detector import AnomalyRiskLevel, FraudFlag, FraudGuardrailEngine


class TestFraudGuardrailEngine(unittest.TestCase):
    """Test suite for FraudGuardrailEngine."""

    def setUp(self):
        self.engine = FraudGuardrailEngine(
            known_partner_ibans={
                "ПЛЕВЕН СТРОЙ ЕООД": "BG77BPBI91001122334455",
            }
        )

    def test_low_risk_normal_transaction(self):
        tx = {
            "item_id": 1,
            "counterparty_name": "ПЛЕВЕН СТРОЙ ЕООД",
            "counterparty_iban": "BG77BPBI91001122334455",
            "narrative_description": "Плащане фактура за строителни материали",
            "debit_amount": 1250.00,
        }
        res = self.engine.evaluate_transaction(tx)
        self.assertEqual(res.risk_level, AnomalyRiskLevel.LOW)
        self.assertEqual(res.risk_score, 0.0)
        self.assertEqual(len(res.flags), 0)

    def test_unverified_iban_flagging(self):
        tx = {
            "item_id": 2,
            "counterparty_name": "ПЛЕВЕН СТРОЙ ЕООД",
            "counterparty_iban": "BG00FAKE00000000000000",
            "narrative_description": "Плащане аванс",
            "debit_amount": 500.00,
        }
        res = self.engine.evaluate_transaction(tx)
        self.assertIn(FraudFlag.UNVERIFIED_IBAN.value, res.flags)
        self.assertGreaterEqual(res.risk_score, 0.50)

    def test_suspicious_keyword_flagging(self):
        tx = {
            "item_id": 3,
            "counterparty_name": "НЕИЗВЕСТЕН ПОЛУЧАТЕЛ",
            "counterparty_iban": "",
            "narrative_description": "ПРЕВОД КАЗИНО КРИПТО ТЕГЛЕНЕ",
            "debit_amount": 300.00,
        }
        res = self.engine.evaluate_transaction(tx)
        self.assertIn(FraudFlag.SUSPICIOUS_KEYWORD.value, res.flags)

    def test_cross_bank_duplicate_batch_flagging(self):
        batch = [
            {
                "item_id": 1,
                "counterparty_name": "ВЕНДОР А",
                "document_number": "INV_1001",
                "debit_amount": 100.00,
            },
            {
                "item_id": 2,
                "counterparty_name": "ВЕНДОР А",
                "document_number": "INV_1001",  # Duplicate document!
                "debit_amount": 100.00,
            },
        ]
        enriched = self.engine.evaluate_batch(batch)
        self.assertEqual(len(enriched), 2)
        self.assertIn(FraudFlag.CROSS_BANK_DUPLICATE.value, enriched[1]["fraud_flags"])
        self.assertEqual(enriched[1]["risk_level"], AnomalyRiskLevel.CRITICAL.value)


if __name__ == "__main__":
    unittest.main()
