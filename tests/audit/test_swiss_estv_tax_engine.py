"""
Unit tests for Swiss ESTV Tax Engine (Swiss Federal Tax Administration MWST).
"""

import tempfile
import unittest
from src.audit.swiss_estv_tax_engine import (
    SwissESTVTaxEngine,
    SwissFilingPeriod,
    SwissUID,
    SwissVATRate,
)


class TestSwissESTVTaxEngine(unittest.TestCase):
    """Test suite for SwissESTVTaxEngine."""

    def test_validate_uid(self):
        self.assertTrue(SwissESTVTaxEngine.validate_uid("CHE-123.456.789 MWST"))
        self.assertTrue(SwissESTVTaxEngine.validate_uid("CHE-987.654.321 TVA"))
        self.assertFalse(SwissESTVTaxEngine.validate_uid("INVALID_UID"))

    def test_calculate_vat_standard_rate(self):
        tx = SwissESTVTaxEngine.calculate_vat(
            transaction_id="CH_TX_001",
            entity_id="ENT_CH",
            net_amount_chf=1000.0,
            rate_type=SwissVATRate.STANDARD,
        )

        self.assertEqual(tx.vat_rate_type, SwissVATRate.STANDARD)
        self.assertEqual(tx.vat_rate_percent, 8.1)
        self.assertEqual(tx.vat_amount_chf, 81.0)
        self.assertEqual(tx.gross_amount_chf, 1081.0)

    def test_calculate_vat_export_zero_rated(self):
        tx = SwissESTVTaxEngine.calculate_vat(
            transaction_id="CH_EXP_001",
            entity_id="ENT_CH",
            net_amount_chf=5000.0,
            rate_type=SwissVATRate.STANDARD,
            is_export=True,
        )

        self.assertEqual(tx.vat_rate_percent, 0.0)
        self.assertEqual(tx.vat_amount_chf, 0.0)

    def test_generate_estv_declaration(self):
        tx1 = SwissESTVTaxEngine.calculate_vat("TX1", "ENT_CH", 10000.0, SwissVATRate.STANDARD)
        tx2 = SwissESTVTaxEngine.calculate_vat("TX2", "ENT_CH", 2000.0, SwissVATRate.REDUCED)

        decl = SwissESTVTaxEngine.generate_estv_declaration(
            entity_id="ENT_CH",
            uid_number="CHE-123.456.789 MWST",
            period_start="2026-01-01",
            period_end="2026-03-31",
            transactions=[tx1, tx2],
            filing_period=SwissFilingPeriod.QUARTERLY,
        )

        self.assertEqual(decl.uid_number, "CHE-123.456.789 MWST")
        self.assertEqual(decl.cipher_200_total_revenue, 12000.0)
        self.assertGreater(decl.cipher_399_total_tax_due, 0.0)

    def test_calculate_withholding_tax_dta(self):
        res = SwissESTVTaxEngine.calculate_withholding_tax(
            gross_dividend_chf=100000.0,
            beneficial_owner_country="DE",
        )

        self.assertEqual(res["gross_dividend_chf"], 100000.0)
        self.assertEqual(res["withholding_rate_percent"], 15.0)
        self.assertEqual(res["withholding_tax_amount_chf"], 15000.0)

    def test_generate_swiss_vat_journal_entries(self):
        tx = SwissESTVTaxEngine.calculate_vat("TX1", "ENT_CH", 1000.0, SwissVATRate.STANDARD)
        entries = SwissESTVTaxEngine.generate_swiss_vat_journal_entries([tx])

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["debit_account"], "503")
        self.assertEqual(entries[0]["credit_account"], "4538")

    def test_generate_estv_xml_export(self):
        tx = SwissESTVTaxEngine.calculate_vat("TX1", "ENT_CH", 1000.0, SwissVATRate.STANDARD)
        decl = SwissESTVTaxEngine.generate_estv_declaration(
            "ENT_CH", "CHE-123.456.789 MWST", "2026-01-01", "2026-03-31", [tx]
        )

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            xml_path = f.name

        out_path = SwissESTVTaxEngine.generate_estv_xml_export(decl, xml_path)
        self.assertEqual(out_path, xml_path)


if __name__ == "__main__":
    unittest.main()
