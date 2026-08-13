"""
Unit tests for US Sales Tax Engine.
"""

import unittest
from src.audit.us_sales_tax_engine import (
    USNexusType,
    USSalesTaxEngine,
)


class TestUSSalesTaxEngine(unittest.TestCase):
    """Test suite for USSalesTaxEngine."""

    def test_determine_nexus_economic(self):
        nexus = USSalesTaxEngine.determine_nexus(
            entity_id="ENT_US",
            state_code="CA",
            annual_revenue=600000.0,
            annual_transactions=300,
        )

        self.assertEqual(nexus.state_code, "CA")
        self.assertTrue(nexus.currently_active)

    def test_calculate_sales_tax_california(self):
        tx = USSalesTaxEngine.calculate_sales_tax(
            transaction_id="US_TX_001",
            entity_id="ENT_US",
            state_code="CA",
            gross_amount=100.0,
        )

        self.assertEqual(tx.state_code, "CA")
        self.assertEqual(tx.combined_tax_rate, 8.56)
        self.assertEqual(tx.tax_amount, 8.56)

    def test_calculate_sales_tax_no_tax_state(self):
        tx = USSalesTaxEngine.calculate_sales_tax(
            transaction_id="US_TX_OR",
            entity_id="ENT_US",
            state_code="OR",
            gross_amount=1000.0,
        )

        self.assertEqual(tx.tax_amount, 0.0)

    def test_generate_state_tax_return(self):
        tx1 = USSalesTaxEngine.calculate_sales_tax("TX1", "ENT_US", "NY", 1000.0)
        tx2 = USSalesTaxEngine.calculate_sales_tax("TX2", "ENT_US", "NY", 500.0)

        ret = USSalesTaxEngine.generate_state_tax_return(
            entity_id="ENT_US",
            state_code="NY",
            period_start="2026-01-01",
            period_end="2026-01-31",
            transactions=[tx1, tx2],
        )

        self.assertEqual(ret.state_code, "NY")
        self.assertEqual(ret.gross_sales, 1500.0)
        self.assertGreater(ret.tax_due, 0.0)

    def test_generate_sales_tax_journal_entries(self):
        tx = USSalesTaxEngine.calculate_sales_tax("TX1", "ENT_US", "TX", 100.0)
        entries = USSalesTaxEngine.generate_sales_tax_journal_entries([tx])

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["debit_account"], "503")
        self.assertEqual(entries[0]["credit_account"], "4537")

    def test_generate_multi_state_summary(self):
        tx_ca = USSalesTaxEngine.calculate_sales_tax("TX_CA", "ENT_US", "CA", 1000.0)
        tx_ny = USSalesTaxEngine.calculate_sales_tax("TX_NY", "ENT_US", "NY", 1000.0)

        summary = USSalesTaxEngine.generate_multi_state_summary(
            entity_id="ENT_US",
            transactions=[tx_ca, tx_ny],
        )

        self.assertEqual(summary["entity_id"], "ENT_US")
        self.assertEqual(summary["total_gross_sales"], 2000.0)
        self.assertIn("CA", summary["state_breakdown"])
        self.assertIn("NY", summary["state_breakdown"])


if __name__ == "__main__":
    unittest.main()
