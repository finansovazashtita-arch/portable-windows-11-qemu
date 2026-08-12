"""
Unit tests for VIES VAT & E-Invoicing Sync Module.
"""

import unittest
from src.integration.vies_vat_checker import VATValidationResult, VIESVATChecker


class TestVIESVATChecker(unittest.TestCase):
    """Test suite for VIESVATChecker."""

    def test_format_vat_number(self):
        c1, v1 = VIESVATChecker.format_vat_number("BG114077876")
        self.assertEqual(c1, "BG")
        self.assertEqual(v1, "114077876")

        c2, v2 = VIESVATChecker.format_vat_number("114077876", default_country="BG")
        self.assertEqual(c2, "BG")
        self.assertEqual(v2, "114077876")

        c3, v3 = VIESVATChecker.format_vat_number("DE123456789")
        self.assertEqual(c3, "DE")
        self.assertEqual(v3, "123456789")

    def test_validate_bg_vat_known_eik(self):
        res = VIESVATChecker.validate_bg_vat("114077876")
        self.assertIsInstance(res, VATValidationResult)
        self.assertEqual(res.country_code, "BG")
        self.assertEqual(res.vat_number, "114077876")
        self.assertTrue(res.valid)

    def test_batch_validate_counterparties(self):
        counterparties = [
            {"name": "СТОРГОЗИЯ АД", "eik": "114077876"},
            {"name": "ПЛЕВЕН СТРОЙ ЕООД", "eik": "999888777"},
            {"name": "НЕИЗВЕСТЕН ВЕНДОР", "eik": ""},
        ]
        enriched = VIESVATChecker.batch_validate_counterparties(counterparties)
        self.assertEqual(len(enriched), 3)

        self.assertTrue(enriched[0]["vies_vat_valid"])
        self.assertEqual(enriched[0]["vies_vat_status"], "VALIDATED")
        self.assertEqual(enriched[2]["vies_vat_status"], "NO_EIK_PROVIDED")


if __name__ == "__main__":
    unittest.main()
