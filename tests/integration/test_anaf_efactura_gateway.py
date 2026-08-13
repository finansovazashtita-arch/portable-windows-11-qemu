"""
Unit & Integration Tests for Romania ANAF e-Factura Gateway (M78).
"""

import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from src.integration.anaf_efactura_gateway import (
    ANAFEInvoiceGateway,
    ANAFInvoice,
    ANAFParty,
    ANAFInvoiceItem,
    ANAFInvoiceType,
    ANAFInvoiceStatus,
    VATCategory,
    ANAFEnvironment,
    ANAFVATRegistryInfo,
    validate_cif
)


class TestANAFValidationUtils(unittest.TestCase):
    """Tests for Romanian CIF / CUI check digit validation algorithm."""

    def test_valid_romanian_cif_with_ro_prefix(self):
        is_valid, clean_cif, formatted = validate_cif("RO12345678")
        self.assertTrue(is_valid)
        self.assertEqual(clean_cif, "12345678")
        self.assertEqual(formatted, "RO12345678")

    def test_valid_romanian_cif_without_ro_prefix(self):
        is_valid, clean_cif, formatted = validate_cif("12345678")
        self.assertTrue(is_valid)
        self.assertEqual(clean_cif, "12345678")
        self.assertEqual(formatted, "RO12345678")

    def test_invalid_romanian_cif_check_digit(self):
        is_valid, clean_cif, formatted = validate_cif("RO12345679")
        self.assertFalse(is_valid)

    def test_invalid_non_numeric_cif(self):
        is_valid, clean_cif, formatted = validate_cif("ROABC12345")
        self.assertFalse(is_valid)

    def test_empty_cif(self):
        is_valid, clean_cif, formatted = validate_cif("")
        self.assertFalse(is_valid)


class TestANAFEInvoiceGateway(unittest.TestCase):
    """Test suite for ANAFEInvoiceGateway core functions."""

    def setUp(self):
        self.gateway = ANAFEInvoiceGateway(environment=ANAFEnvironment.TEST)
        self.supplier = ANAFParty(
            cif="RO114077876",
            name="FINANSPROTECT ROMANIA SRL",
            trade_register_no="J40/100/2022",
            address="Calea Victoriei 100",
            city="București",
            county="București",
            zip_code="010091",
            country_code="RO",
            iban="RO98BTRL12345678901234XX",
            bank_name="Banca Transilvania",
            vat_registered=True
        )
        self.customer = ANAFParty(
            cif="RO12345678",
            name="ROBOTICS SOFTWARE SERVICES SRL",
            trade_register_no="J12/500/2020",
            address="Bulevardul Unirii 10",
            city="București",
            county="București",
            zip_code="030167",
            country_code="RO",
            vat_registered=True
        )
        self.item = ANAFInvoiceItem(
            line_id="1",
            description="Software Development & Accounting Audit",
            quantity=10.0,
            unit_of_measure="H87",
            unit_price=450.00,
            vat_rate=19.0,
            vat_category=VATCategory.STANDARD
        )
        self.invoice = ANAFInvoice(
            invoice_id="INV-RO-2026-0001",
            series="FPS",
            number="000101",
            issue_date="2026-08-13",
            due_date="2026-09-12",
            supplier=self.supplier,
            customer=self.customer,
            items=[self.item],
            currency="RON"
        )

    def test_invoice_totals_computation(self):
        self.assertEqual(self.invoice.total_net_amount, 4500.00)
        self.assertEqual(self.invoice.total_vat_amount, 855.00)
        self.assertEqual(self.invoice.total_payable_amount, 5355.00)

    def test_generate_ro_cius_xml_valid_structure(self):
        xml_content = self.gateway.generate_ro_cius_xml(self.invoice)
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', xml_content)
        self.assertIn('urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1', xml_content)
        self.assertIn('reporting:RO-CIUS', xml_content)
        self.assertIn('FINANSPROTECT ROMANIA SRL', xml_content)
        self.assertIn('RO114077876', xml_content)
        self.assertIn('RO12345678', xml_content)
        self.assertIn('5355.00', xml_content)

        # Parse XML to ensure valid syntax
        root = ET.fromstring(xml_content)
        self.assertEqual(root.tag.split('}')[-1], 'Invoice')

    def test_validate_ro_cius_rules_success(self):
        res = self.gateway.validate_ro_cius_rules(self.invoice)
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["errors"]), 0)

    def test_validate_ro_cius_rules_invalid_cif(self):
        bad_supplier = ANAFParty(cif="RO99999999", name="BAD CIF SRL")
        bad_inv = ANAFInvoice(
            invoice_id="INV-BAD-01",
            series="FPS",
            number="01",
            issue_date="2026-08-13",
            due_date="2026-09-12",
            supplier=bad_supplier,
            customer=self.customer,
            items=[self.item]
        )
        res = self.gateway.validate_ro_cius_rules(bad_inv)
        self.assertFalse(res["valid"])
        self.assertTrue(any("invalid under Romanian tax ID" in e for e in res["errors"]))

    def test_sign_xml_payload(self):
        xml_content = self.gateway.generate_ro_cius_xml(self.invoice)
        signed_xml = self.gateway.sign_xml_payload(xml_content)
        self.assertIn("<ext:UBLExtensions>", signed_xml)
        self.assertIn("ANAF_QES_SIG_", signed_xml)
        self.assertIn("<SignatureValue>", signed_xml)

    def test_upload_invoice_end_to_end(self):
        res = self.gateway.upload_invoice(self.invoice)
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["upload_id"])
        self.assertIsNotNone(res["download_id"])
        self.assertEqual(res["status"], "ACCEPTED")

    def test_query_processing_status(self):
        upload_res = self.gateway.upload_invoice(self.invoice)
        status_res = self.gateway.query_processing_status(upload_res["upload_id"])
        self.assertEqual(status_res["upload_id"], upload_res["upload_id"])
        self.assertEqual(status_res["status"], "ACCEPTED")

    def test_download_response(self):
        dl_res = self.gateway.download_response("DL-TEST-998877")
        self.assertTrue(dl_res["success"])
        self.assertIn("ANAFValidationReceipt", dl_res["xml_content"])

    def test_check_vat_registry(self):
        info = self.gateway.check_vat_registry("RO12345678")
        self.assertIsInstance(info, ANAFVATRegistryInfo)
        self.assertEqual(info.cif, "RO12345678")
        self.assertTrue(info.vat_registered)


if __name__ == "__main__":
    unittest.main()
