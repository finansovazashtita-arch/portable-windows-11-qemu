"""
Unit tests for Autonomous Corporate Income Tax (CITA / ЗКПО) Tax Return Generator.
"""

import unittest

from src.audit.corporate_tax_return import (
    AnnualTaxableAdjustment,
    CorporateTaxReturnGenerator,
    TaxableAdjustmentType,
)


class TestCorporateTaxReturnGenerator(unittest.TestCase):
    """Test suite for CorporateTaxReturnGenerator."""

    def test_calculate_corporate_tax_with_adjustments(self):
        adj1 = AnnualTaxableAdjustment(
            description="Непризнати разходи без документи (Сметка 609)",
            adjustment_type=TaxableAdjustmentType.NON_DEDUCTIBLE_EXPENSE,
            amount_eur=5000.0,
        )

        res = CorporateTaxReturnGenerator.calculate_corporate_tax(
            year=2026,
            accounting_profit_eur=50000.0,
            adjustments=[adj1],
            tax_rate_percent=10.0,
        )

        self.assertEqual(res.year, 2026)
        self.assertEqual(res.accounting_profit_eur, 50000.0)
        self.assertEqual(res.total_increases_eur, 5000.0)
        self.assertEqual(res.taxable_profit_eur, 55000.0)
        self.assertEqual(res.corporate_tax_due_eur, 5500.0)

    def test_generate_corporate_tax_journal_entries(self):
        res = CorporateTaxReturnGenerator.calculate_corporate_tax(
            year=2026,
            accounting_profit_eur=10000.0,
            adjustments=[],
            tax_rate_percent=10.0,
        )
        entries = CorporateTaxReturnGenerator.generate_corporate_tax_journal_entries(res)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["debit_account"], "123")
        self.assertEqual(entries[0]["credit_account"], "454")
        self.assertEqual(entries[0]["amount_eur"], 1000.0)


if __name__ == "__main__":
    unittest.main()
