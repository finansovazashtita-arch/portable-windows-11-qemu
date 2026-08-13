"""
Unit tests for Automated Regulatory E-Reporting Adapter Engine for NRA Bulgarian VAT.
"""

import os
import tempfile
import unittest

from src.audit.nra_vat_reporter import NRAVATDeclaration, NRAVATReporter, VATPeriod


class TestNRAVATReporter(unittest.TestCase):
    """Test suite for NRAVATReporter."""

    def setUp(self):
        self.period = VATPeriod(year=2026, month=1)
        self.declaration = NRAVATDeclaration(
            eik="824009825",
            company_name="СТОРОГОЗИЯ АД",
            vat_period=self.period,
            taxable_base_20=10000.00,
            vat_tax_20=2000.00,
            purchases_taxable_base_20=6000.00,
            purchases_vat_credit_20=1200.00,
        )
        self.purchases = [
            {
                "doc_num": "10002489",
                "doc_date": "2026-01-15",
                "supplier_eik": "121302219",
                "supplier_name": "ОМВ БЪЛГАРИЯ ООД",
                "base_amount": 5000.00,
                "vat_amount": 1000.00,
            }
        ]
        self.sales = [
            {
                "doc_num": "4589",
                "doc_date": "2026-01-20",
                "client_eik": "131456987",
                "client_name": "АЕН БЪЛГАРИЯ ЕООД",
                "base_amount": 10000.00,
                "vat_amount": 2000.00,
            }
        ]

    def test_vat_cell_calculations(self):
        self.assertEqual(self.declaration.net_vat_payable, 800.00)
        self.assertEqual(self.declaration.net_vat_refundable, 0.0)

    def test_generate_declar_txt(self):
        txt = NRAVATReporter.generate_declar_txt(self.declaration)
        self.assertIn("HEADER|DEKLAR|202601|EIK:824009825|СТОРОГОЗИЯ АД", txt)
        self.assertIn("CELL11|10000.00", txt)
        self.assertIn("CELL21|2000.00", txt)
        self.assertIn("CELL50|800.00", txt)

    def test_export_vat_package(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res = NRAVATReporter.export_vat_package(self.declaration, self.purchases, self.sales, tmpdir)

            self.assertTrue(os.path.exists(res["DEKLAR"]))
            self.assertTrue(os.path.exists(res["POKUPKI"]))
            self.assertTrue(os.path.exists(res["PRODAGBI"]))


if __name__ == "__main__":
    unittest.main()
