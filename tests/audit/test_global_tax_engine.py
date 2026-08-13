"""
Unit tests for Global Multi-Entity Tax & VAT Engine (m62_global_multinational_tax_engine).
"""

import unittest
from src.audit.global_tax_engine import (
    FilingFrequency,
    GlobalMultiEntityTaxEngine,
    TaxFilingStatus,
    TaxJurisdiction,
    TaxType,
)


class TestGlobalMultiEntityTaxEngine(unittest.TestCase):
    """Test suite for GlobalMultiEntityTaxEngine."""

    def test_calculate_tax_bulgaria_vat(self):
        tx = GlobalMultiEntityTaxEngine.calculate_tax(
            transaction_id="TX_BG_001",
            entity_id="ENT_BG",
            jurisdiction=TaxJurisdiction.BULGARIA,
            tax_type=TaxType.VAT,
            net_amount=1000.0,
            currency="EUR",
        )

        self.assertEqual(tx.jurisdiction, TaxJurisdiction.BULGARIA)
        self.assertEqual(tx.tax_rate_percent, 20.0)
        self.assertEqual(tx.tax_amount, 200.0)
        self.assertEqual(tx.gross_amount, 1200.0)

    def test_calculate_tax_us_sales_tax(self):
        tx = GlobalMultiEntityTaxEngine.calculate_tax(
            transaction_id="TX_US_001",
            entity_id="ENT_US",
            jurisdiction=TaxJurisdiction.UNITED_STATES,
            tax_type=TaxType.SALES_TAX,
            net_amount=500.0,
            currency="USD",
            us_state="CA",
        )

        self.assertEqual(tx.jurisdiction, TaxJurisdiction.UNITED_STATES)
        self.assertEqual(tx.tax_rate_percent, 7.25)
        self.assertEqual(tx.tax_amount, 36.25)
        self.assertEqual(tx.gross_amount, 536.25)

    def test_calculate_reverse_charge_vat(self):
        tx = GlobalMultiEntityTaxEngine.calculate_reverse_charge_vat(
            transaction_id="RC_DE_BG_01",
            entity_id="ENT_BG",
            seller_jurisdiction=TaxJurisdiction.EU_OSS,
            buyer_jurisdiction=TaxJurisdiction.BULGARIA,
            net_amount=2000.0,
            currency="EUR",
        )

        self.assertEqual(tx.tax_rate_percent, 20.0)
        self.assertEqual(tx.tax_amount, 400.0)
        self.assertEqual(tx.gross_amount, 2400.0)

    def test_generate_tax_journal_entries(self):
        tx1 = GlobalMultiEntityTaxEngine.calculate_tax("TX1", "ENT1", TaxJurisdiction.BULGARIA, TaxType.VAT, 100.0, "EUR")
        tx2 = GlobalMultiEntityTaxEngine.calculate_tax("TX2", "ENT2", TaxJurisdiction.UNITED_KINGDOM, TaxType.VAT, 100.0, "GBP")

        entries = GlobalMultiEntityTaxEngine.generate_tax_journal_entries([tx1, tx2])

        self.assertGreaterEqual(len(entries), 2)
        self.assertEqual(entries[0]["debit_account"], "503")
        self.assertEqual(entries[0]["credit_account"], "4532")

    def test_generate_tax_filing(self):
        tx1 = GlobalMultiEntityTaxEngine.calculate_tax(
            "TX_F1", "ENT_GROUP_1", TaxJurisdiction.BULGARIA, TaxType.VAT, 1000.0, "EUR", transaction_date="2026-01-15"
        )
        filing = GlobalMultiEntityTaxEngine.generate_tax_filing(
            entity_id="ENT_GROUP_1",
            jurisdiction=TaxJurisdiction.BULGARIA,
            period_start="2026-01-01",
            period_end="2026-03-31",
            transactions=[tx1],
            filing_frequency=FilingFrequency.QUARTERLY,
        )

        self.assertEqual(filing.entity_id, "ENT_GROUP_1")
        self.assertEqual(filing.jurisdiction, TaxJurisdiction.BULGARIA)
        self.assertEqual(filing.status, TaxFilingStatus.DRAFT)
        self.assertEqual(filing.total_tax_payable, 200.0)

    def test_consolidate_group_tax_position(self):
        tx_bg = GlobalMultiEntityTaxEngine.calculate_tax("TX_BG", "ENT_BG", TaxJurisdiction.BULGARIA, TaxType.VAT, 1000.0, "EUR", transaction_date="2026-01-10")
        tx_uk = GlobalMultiEntityTaxEngine.calculate_tax("TX_UK", "ENT_UK", TaxJurisdiction.UNITED_KINGDOM, TaxType.VAT, 2000.0, "GBP", transaction_date="2026-01-12")

        entities = [
            {"entity_id": "ENT_BG", "entity_name": "Bulgaria Sub Ltd"},
            {"entity_id": "ENT_UK", "entity_name": "UK Sub Ltd"},
        ]

        summary = GlobalMultiEntityTaxEngine.consolidate_group_tax_position(
            entities=entities,
            period_start="2026-01-01",
            period_end="2026-01-31",
            transactions=[tx_bg, tx_uk],
        )

        self.assertGreater(summary.total_group_tax_liability, 0.0)
        self.assertIn("BULGARIA", summary.jurisdictions_covered)
        self.assertIn("UNITED_KINGDOM", summary.jurisdictions_covered)


if __name__ == "__main__":
    unittest.main()
