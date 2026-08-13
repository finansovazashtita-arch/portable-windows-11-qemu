"""
Unit tests for Autonomous Business Travel Expenses & Per Diem Allowance Manager (Account 609 / Наредба за командировките).
"""

import unittest

from src.accounting.travel_expense_manager import BusinessTravelOrder, TravelExpenseManager, TravelType


class TestTravelExpenseManager(unittest.TestCase):
    """Test suite for TravelExpenseManager."""

    def test_process_domestic_travel_order(self):
        order = BusinessTravelOrder(
            order_id="TRV_001",
            employee_name="Георги Попов",
            destination="Варна",
            travel_type=TravelType.DOMESTIC,
            days_count=3,
            per_diem_daily_rate_eur=20.0,
            lodging_total_eur=120.0,
            transport_total_eur=40.0,
        )

        report = TravelExpenseManager.process_travel_order(order)

        self.assertEqual(report.total_per_diem_eur, 60.0)  # 3 * 20
        self.assertEqual(report.total_travel_expense_eur, 220.0)  # 60 + 120 + 40
        self.assertEqual(len(report.journal_entries), 1)
        self.assertEqual(report.journal_entries[0]["debit_account"], "609")
        self.assertEqual(report.journal_entries[0]["credit_account"], "422")
        self.assertEqual(report.journal_entries[0]["amount_eur"], 220.0)

    def test_process_international_travel_order(self):
        order = BusinessTravelOrder(
            order_id="TRV_002",
            employee_name="Мария Петрова",
            destination="Франкфурт, Германия",
            travel_type=TravelType.INTERNATIONAL,
            days_count=5,
            per_diem_daily_rate_eur=50.0,
            lodging_total_eur=400.0,
            transport_total_eur=250.0,
        )

        report = TravelExpenseManager.process_travel_order(order)

        self.assertEqual(report.total_per_diem_eur, 250.0)  # 5 * 50
        self.assertEqual(report.total_travel_expense_eur, 900.0)  # 250 + 400 + 250
        self.assertEqual(report.journal_entries[0]["amount_eur"], 900.0)


if __name__ == "__main__":
    unittest.main()
