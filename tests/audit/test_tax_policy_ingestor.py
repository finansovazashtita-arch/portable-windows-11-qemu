"""
Unit tests for Autonomous Tax Policy & Regulatory Update Ingestion Engine.
"""

import unittest

from src.audit.tax_policy_ingestor import AutonomousTaxPolicyIngestor, RegulationChangeType


class TestAutonomousTaxPolicyIngestor(unittest.TestCase):
    """Test suite for AutonomousTaxPolicyIngestor."""

    def test_ingest_vat_rate_change(self):
        update = AutonomousTaxPolicyIngestor.ingest_gazette_update(
            gazette_issue_num="102/2026",
            raw_text="Закон за изменение на ЗДДС: Изменение в данъчната ставка по ДДС за ресторантьорски услуги.",
        )

        self.assertEqual(update.gazette_issue_num, "102/2026")
        self.assertEqual(update.change_type, RegulationChangeType.VAT_RATE_CHANGE)
        self.assertIn("4531", update.impacted_accounts)
        self.assertFalse(update.is_applied)

    def test_apply_policy_updates(self):
        update = AutonomousTaxPolicyIngestor.ingest_gazette_update(
            gazette_issue_num="105/2026",
            raw_text="Ново счетоводно решение за изменение на Националния сметкоплан за сметки 604 и 454.",
        )

        res = AutonomousTaxPolicyIngestor.apply_policy_updates(update)
        self.assertEqual(res["status"], "POLICY_APPLIED")
        self.assertTrue(update.is_applied)


if __name__ == "__main__":
    unittest.main()
