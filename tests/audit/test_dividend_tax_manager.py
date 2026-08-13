"""
Unit tests for Autonomous Personal Income Tax & Dividend Withholding Tax Manager.
"""

import unittest

from src.audit.dividend_tax_manager import DividendBeneficiaryType, DividendTaxManager


class TestDividendTaxManager(unittest.TestCase):
    """Test suite for DividendTaxManager."""

    def test_process_dividend_payout_physical_person(self):
        payout = DividendTaxManager.process_dividend_payout(
            payout_id="DIV_001",
            shareholder_name="Иван Иванов",
            beneficiary_type=DividendBeneficiaryType.PHYSICAL_PERSON,
            gross_dividend_eur=10000.0,
        )

        self.assertEqual(payout.withholding_tax_rate_percent, 5.0)
        self.assertEqual(payout.withholding_tax_due_eur, 500.0)
        self.assertEqual(payout.net_dividend_eur, 9500.0)

    def test_process_dividend_payout_eu_entity(self):
        payout = DividendTaxManager.process_dividend_payout(
            payout_id="DIV_002",
            shareholder_name="Holding BV Netherlands",
            beneficiary_type=DividendBeneficiaryType.EU_LEGAL_ENTITY,
            gross_dividend_eur=100000.0,
        )

        self.assertEqual(payout.withholding_tax_rate_percent, 0.0)
        self.assertEqual(payout.withholding_tax_due_eur, 0.0)
        self.assertEqual(payout.net_dividend_eur, 100000.0)

    def test_generate_dividend_journal_entries(self):
        payout = DividendTaxManager.process_dividend_payout(
            payout_id="DIV_003",
            shareholder_name="Петър Петров",
            beneficiary_type=DividendBeneficiaryType.PHYSICAL_PERSON,
            gross_dividend_eur=20000.0,
        )

        entries = DividendTaxManager.generate_dividend_journal_entries(payout)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["debit_account"], "122")
        self.assertEqual(entries[0]["credit_account"], "425")
        self.assertEqual(entries[0]["amount_eur"], 19000.0)

        self.assertEqual(entries[1]["debit_account"], "122")
        self.assertEqual(entries[1]["credit_account"], "454")
        self.assertEqual(entries[1]["amount_eur"], 1000.0)

    def test_generate_form55_declaration(self):
        p1 = DividendTaxManager.process_dividend_payout("DIV_01", "Owner 1", DividendBeneficiaryType.PHYSICAL_PERSON, 10000.0)
        p2 = DividendTaxManager.process_dividend_payout("DIV_02", "Owner 2", DividendBeneficiaryType.PHYSICAL_PERSON, 10000.0)

        form55 = DividendTaxManager.generate_form55_declaration(year=2026, quarter_num=2, payouts=[p1, p2])

        self.assertEqual(form55["year"], 2026)
        self.assertEqual(form55["quarter"], "Q2")
        self.assertEqual(form55["total_gross_dividends_eur"], 20000.0)
        self.assertEqual(form55["total_withholding_tax_due_eur"], 1000.0)


if __name__ == "__main__":
    unittest.main()
