"""
Unit tests for Peppol Cross-Border EU E-Invoicing & Network Integration Engine.
"""

import unittest

from src.integration.peppol_einvoicing import PeppolEInvoicingEngine, PeppolInvoice


class TestPeppolEInvoicing(unittest.TestCase):
    """Test suite for PeppolEInvoicingEngine."""

    def test_validate_en16931_valid_invoice(self):
        invoice = PeppolInvoice(
            invoice_id="INV_2026_001",
            issue_date="2026-01-31",
            supplier_endpoint_id="9925:BG123456789",
            customer_endpoint_id="9925:BG987654321",
            total_amount=1500.00,
            vat_amount=300.00,
            currency="EUR",
        )
        self.assertTrue(PeppolEInvoicingEngine.validate_en16931(invoice))

    def test_generate_peppol_ubl_xml_structure(self):
        invoice = PeppolInvoice(
            invoice_id="INV_2026_002",
            issue_date="2026-01-31",
            supplier_endpoint_id="9925:BG123456789",
            customer_endpoint_id="9925:BG987654321",
            total_amount=2400.00,
            vat_amount=480.00,
            currency="EUR",
        )
        xml_str = PeppolEInvoicingEngine.generate_peppol_ubl_xml(invoice)

        self.assertIn("urn:oasis:names:specification:ubl:schema:xsd:Invoice-2", xml_str)
        self.assertIn("<cbc:ID>INV_2026_002</cbc:ID>", xml_str)
        self.assertIn('<cbc:PayableAmount currencyID="EUR">2400.00</cbc:PayableAmount>', xml_str)


if __name__ == "__main__":
    unittest.main()
