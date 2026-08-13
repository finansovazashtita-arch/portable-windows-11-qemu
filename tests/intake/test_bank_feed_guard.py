"""
Unit tests for Automated Real-Time Bank Account Reconciliation Guard (Bank Feed Guard).
"""

import unittest

from src.intake.bank_feed_guard import BankFeedGuard, BankFeedItem, BankFeedStatus


class TestBankFeedGuard(unittest.TestCase):
    """Test suite for BankFeedGuard."""

    def test_reconcile_matched_bank_item(self):
        item = BankFeedItem(
            transaction_id="TX_101",
            date="2026-06-15",
            amount_eur=150.0,
            is_debit=True,
            narrative="Плащане на фактура 1002",
        )
        ledger_entries = [{"amount_eur": 150.0, "is_credit": False}]

        res = BankFeedGuard.reconcile_feed_item(item, ledger_entries)
        self.assertEqual(res.status, BankFeedStatus.MATCHED)

    def test_reconcile_unposted_bank_fee(self):
        item = BankFeedItem(
            transaction_id="TX_102",
            date="2026-06-15",
            amount_eur=2.50,
            is_debit=True,
            narrative="Месечна банкова такса за обслужване на сметка",
        )
        ledger_entries = []

        res = BankFeedGuard.reconcile_feed_item(item, ledger_entries)
        self.assertEqual(res.status, BankFeedStatus.UNPOSTED_BANK_FEE)

    def test_run_realtime_guard(self):
        item1 = BankFeedItem("TX_1", "2026-06-15", 500.0, False, "Превод от клиент")
        item2 = BankFeedItem("TX_2", "2026-06-15", 3.00, True, "Такса превод")

        ledger_entries = [{"amount_eur": 500.0, "is_credit": True}]  # Ledger knows item1, but not fee item2

        summary = BankFeedGuard.run_realtime_guard(
            bank_items=[item1, item2],
            ledger_503_entries=ledger_entries,
            bank_opening_balance=1000.0,
            ledger_opening_balance=1000.0,
        )

        self.assertEqual(summary.matched_count, 1)
        self.assertEqual(summary.unposted_bank_fees_count, 1)
        self.assertEqual(len(summary.proposed_fee_entries), 1)
        self.assertEqual(summary.proposed_fee_entries[0]["debit_account"], "621")
        self.assertEqual(summary.proposed_fee_entries[0]["credit_account"], "503")
        self.assertEqual(summary.proposed_fee_entries[0]["amount_eur"], 3.00)


if __name__ == "__main__":
    unittest.main()
