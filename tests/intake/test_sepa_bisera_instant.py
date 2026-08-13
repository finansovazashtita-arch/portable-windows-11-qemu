"""
Unit tests for Multi-Bank SEPA Instant & BISERA 6 Payment Settlement Adapter Engine.
"""

import unittest

from src.intake.sepa_bisera_instant import InstantPaymentTransaction, PaymentSystem, SEPABiseraInstantAdapter


class TestSEPABiseraInstantAdapter(unittest.TestCase):
    """Test suite for SEPABiseraInstantAdapter."""

    def test_process_instant_payment(self):
        tx = SEPABiseraInstantAdapter.process_instant_payment(
            transaction_ref="BISERA6_9941205",
            iban="BG71STSA93000028013479",
            counterparty="СТОРОГОЗИЯ АД",
            amount=1200.50,
            payment_system=PaymentSystem.BISERA_6,
        )

        self.assertEqual(tx.transaction_ref, "BISERA6_9941205")
        self.assertEqual(tx.payment_system, PaymentSystem.BISERA_6)
        self.assertTrue(tx.is_settled)
        self.assertGreater(tx.settlement_time_ms, 0)

    def test_reconcile_with_accounts_payable(self):
        tx = SEPABiseraInstantAdapter.process_instant_payment(
            transaction_ref="SEPA_INST_4011",
            iban="BG18UNCR70001524896512",
            counterparty="ОМВ БЪЛГАРИЯ ООД",
            amount=500.00,
            payment_system=PaymentSystem.SEPA_INSTANT,
            currency="EUR",
        )

        pending = [{"invoice_id": "INV_10024", "amount": 500.00}]
        res = SEPABiseraInstantAdapter.reconcile_with_accounts_payable(tx, pending)

        self.assertEqual(res["status"], "RECONCILED")
        self.assertEqual(res["matched_invoice_id"], "INV_10024")
        self.assertEqual(res["account_dr"], "401")
        self.assertEqual(res["account_cr"], "503")


if __name__ == "__main__":
    unittest.main()
