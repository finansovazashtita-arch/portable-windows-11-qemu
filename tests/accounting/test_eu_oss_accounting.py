"""
Unit tests for Autonomous Cross-Border EU Tax & OSS E-Commerce Invoicing Adapter Engine.
"""

import unittest

from src.accounting.eu_oss_accounting import EUOSSAccountingAdapter, OSSDeclarationQuarter


class TestEUOSSAccountingAdapter(unittest.TestCase):
    """Test suite for EUOSSAccountingAdapter."""

    def test_process_eu_b2c_sale_germany(self):
        tx = EUOSSAccountingAdapter.process_eu_b2c_sale(
            transaction_id="OSS_DE_9901",
            country_code="DE",
            net_amount_eur=100.0,
        )

        self.assertEqual(tx.country_code, "DE")
        self.assertEqual(tx.vat_rate_percent, 19.0)
        self.assertEqual(tx.vat_amount_eur, 19.0)
        self.assertEqual(tx.gross_amount_eur, 119.0)

    def test_generate_oss_journal_entries(self):
        tx1 = EUOSSAccountingAdapter.process_eu_b2c_sale("OSS_FR_01", "FR", 200.0)
        entries = EUOSSAccountingAdapter.generate_oss_journal_entries([tx1])

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["account_cr"], "702")
        self.assertEqual(entries[1]["account_cr"], "4535")
        self.assertEqual(entries[1]["amount_eur"], 40.0)

    def test_generate_quarterly_oss_report(self):
        tx1 = EUOSSAccountingAdapter.process_eu_b2c_sale("OSS_DE_01", "DE", 100.0)
        tx2 = EUOSSAccountingAdapter.process_eu_b2c_sale("OSS_IT_01", "IT", 100.0)

        report = EUOSSAccountingAdapter.generate_quarterly_oss_report(
            year=2026,
            quarter=OSSDeclarationQuarter.Q1,
            sales=[tx1, tx2],
        )

        self.assertEqual(report["year"], 2026)
        self.assertEqual(report["quarter"], "Q1")
        self.assertEqual(report["total_sales_count"], 2)
        self.assertEqual(report["total_net_eur"], 200.0)
        self.assertEqual(report["total_vat_eur"], 41.0)


if __name__ == "__main__":
    unittest.main()
