"""
Unit tests for Autonomous Tax Audit Defense & Discrepancy Risk Scoring Engine.
"""

import unittest

from src.audit.tax_audit_defense import AuditRiskLevel, TaxAuditDefenseEngine


class TestTaxAuditDefenseEngine(unittest.TestCase):
    """Test suite for TaxAuditDefenseEngine."""

    def test_low_risk_evaluation(self):
        eval_res = TaxAuditDefenseEngine.evaluate_audit_risk(
            vat_refundable_amount=0.0,
            vat_payable_amount=1500.0,
            purchase_invoices=[{"doc_num": "1001", "supplier_eik": "121302219"}],
            sales_invoices=[{"doc_num": "4589", "client_eik": "824009825"}],
        )

        self.assertEqual(eval_res.risk_level, AuditRiskLevel.LOW_RISK)
        self.assertFalse(eval_res.art92_vat_refund_flag)
        self.assertEqual(eval_res.missing_invoices_count, 0)

    def test_high_audit_risk_art92_and_deregistered(self):
        eval_res = TaxAuditDefenseEngine.evaluate_audit_risk(
            vat_refundable_amount=12500.0,
            vat_payable_amount=0.0,
            purchase_invoices=[
                {"doc_num": "", "supplier_eik": "999999999"},
                {"doc_num": "1002", "supplier_eik": "121302219"},
            ],
            sales_invoices=[],
            known_deregistered_eiks=["999999999"],
        )

        self.assertEqual(eval_res.risk_level, AuditRiskLevel.HIGH_AUDIT_RISK)
        self.assertTrue(eval_res.art92_vat_refund_flag)
        self.assertEqual(eval_res.missing_invoices_count, 1)
        self.assertIn("999999999", eval_res.deregistered_vat_counterparties)


if __name__ == "__main__":
    unittest.main()
