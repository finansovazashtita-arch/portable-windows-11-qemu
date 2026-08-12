"""
Unit tests for Multi-Modal Document Reconciliation Engine.
"""

import unittest

from src.ai.multimodal_reconciler import MultiModalReconciler, ReconciliationStatus


class TestMultiModalReconciler(unittest.TestCase):
    """Test suite for MultiModalReconciler."""

    def test_reconcile_3way_exact_match(self):
        invoices = [{"doc_number": "100234", "amount": 1250.00}]
        receipts = [{"receipt_id": "REC_55", "amount": 1250.00}]
        bank_txs = [{"item_id": 1, "debit_amount": 1250.00}]

        matches = MultiModalReconciler.reconcile_3way(invoices, receipts, bank_txs)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].status, ReconciliationStatus.MATCHED)
        self.assertEqual(matches[0].match_confidence, 0.99)

    def test_reconcile_invoice_bank_missing_receipt(self):
        invoices = [{"doc_number": "100235", "amount": 500.00}]
        receipts = []
        bank_txs = [{"item_id": 2, "debit_amount": 500.00}]

        matches = MultiModalReconciler.reconcile_3way(invoices, receipts, bank_txs)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].status, ReconciliationStatus.MATCHED)
        self.assertEqual(matches[0].receipt_id, "MISSING")

    def test_reconcile_unmatched_invoice(self):
        invoices = [{"doc_number": "999999", "amount": 9999.00}]
        receipts = []
        bank_txs = []

        matches = MultiModalReconciler.reconcile_3way(invoices, receipts, bank_txs)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].status, ReconciliationStatus.UNMATCHED)


if __name__ == "__main__":
    unittest.main()
