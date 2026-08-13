"""
Unit tests for Autonomous Cash Desk & Petty Cash Management Engine (Account 501 / ПКО & РКО).
"""

import unittest

from src.accounting.cash_desk_manager import CashDeskManager, CashOrder, CashOrderType


class TestCashDeskManager(unittest.TestCase):
    """Test suite for CashDeskManager."""

    def test_process_pko_receipt_order(self):
        order = CashOrder(
            order_id="101",
            date="2026-06-15",
            order_type=CashOrderType.RECEIPT_ORDER,
            amount_eur=250.0,
            counterparty_name="ТехноМаг ЕООД",
            counterparty_account="411",
            narrative="Плащане в брой по фактура 5001",
        )
        entry = CashDeskManager.process_cash_order(order)

        self.assertEqual(entry["debit_account"], "501")
        self.assertEqual(entry["credit_account"], "411")
        self.assertEqual(entry["amount_eur"], 250.0)

    def test_process_rko_expense_order(self):
        order = CashOrder(
            order_id="102",
            date="2026-06-15",
            order_type=CashOrderType.EXPENSE_ORDER,
            amount_eur=50.0,
            counterparty_name="Офис Консумативи АД",
            counterparty_account="601",
            narrative="Покупка на канцеларски материали",
        )
        entry = CashDeskManager.process_cash_order(order)

        self.assertEqual(entry["debit_account"], "601")
        self.assertEqual(entry["credit_account"], "501")
        self.assertEqual(entry["amount_eur"], 50.0)

    def test_generate_daily_cash_book_and_limit_check(self):
        pko = CashOrder("1", "2026-06-15", CashOrderType.RECEIPT_ORDER, 6000.0, "Клиент 1", "411", "Приход")
        rko = CashOrder("2", "2026-06-15", CashOrderType.EXPENSE_ORDER, 500.0, "Доставчик 1", "401", "Разход")

        summary = CashDeskManager.generate_daily_cash_book(
            date_str="2026-06-15",
            orders=[pko, rko],
            opening_balance_eur=1000.0,
            cash_limit_eur=5000.0,
        )

        self.assertEqual(summary.opening_balance_eur, 1000.0)
        self.assertEqual(summary.total_receipts_eur, 6000.0)
        self.assertEqual(summary.total_expenses_eur, 500.0)
        self.assertEqual(summary.closing_balance_eur, 6500.0)
        self.assertTrue(summary.limit_exceeded_flag)  # 6500 > 5000 limit
        self.assertEqual(len(summary.journal_entries), 2)


if __name__ == "__main__":
    unittest.main()
