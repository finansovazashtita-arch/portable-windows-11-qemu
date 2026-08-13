"""
Unit tests for Romania ANAF e-Factura REST API Router & Handlers (M78).
"""

import unittest
from src.integration.anaf_api import (
    get_anaf_health_handler,
    post_anaf_oauth_token_handler,
    post_anaf_generate_xml_handler,
    post_anaf_validate_handler,
    post_anaf_submit_handler,
    get_anaf_status_handler,
    get_anaf_download_handler,
    post_anaf_vat_check_handler,
    get_anaf_invoices_handler
)


class TestANAFAPIRouter(unittest.TestCase):
    """Test suite for ANAF REST API router handlers."""

    def test_health_handler(self):
        res = get_anaf_health_handler({})
        self.assertEqual(res["status"], "ONLINE")
        self.assertIn("Romania ANAF e-Factura Gateway", res["service"])
        self.assertEqual(res["ro_cius_specification"], "1.0.1")

    def test_oauth_token_handler(self):
        res = post_anaf_oauth_token_handler({"auth_code": "mock_code_test_123"})
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["access_token"].startswith("anaf_"))

    def test_generate_xml_handler(self):
        payload = {
            "invoice_id": "INV-API-RO-001",
            "series": "FPS",
            "number": "001",
            "issue_date": "2026-08-13",
            "due_date": "2026-09-12",
            "supplier": {"cif": "RO114077876", "name": "FINANSPROTECT ROMANIA SRL"},
            "customer": {"cif": "RO12345678", "name": "ROBOTICS SOFTWARE SERVICES SRL"},
            "items": [{
                "line_id": "1",
                "description": "IT Audit Services",
                "quantity": 1,
                "unit_price": 1000.00,
                "vat_rate": 19.0
            }]
        }
        res = post_anaf_generate_xml_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["valid"])
        self.assertIn("urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1", res["ubl_xml"])

    def test_validate_handler(self):
        payload = {
            "invoice_id": "INV-API-RO-002",
            "supplier": {"cif": "RO114077876", "name": "SUPPLIER SRL"},
            "customer": {"cif": "RO12345678", "name": "CUSTOMER SRL"},
            "items": [{"description": "Item 1", "quantity": 2, "unit_price": 100.0}]
        }
        res = post_anaf_validate_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["valid"])

    def test_submit_handler(self):
        payload = {
            "invoice_id": "INV-API-SUBMIT-001",
            "supplier": {"cif": "RO114077876", "name": "SUPPLIER SRL"},
            "customer": {"cif": "RO12345678", "name": "CUSTOMER SRL"},
            "items": [{"description": "Cloud Service", "quantity": 1, "unit_price": 500.0}]
        }
        res = post_anaf_submit_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertIsNotNone(res["upload_id"])

    def test_vat_check_handler(self):
        res = post_anaf_vat_check_handler({"cif": "RO12345678"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["cif"], "RO12345678")
        self.assertTrue(res["vat_registered"])

    def test_invoices_query_handler(self):
        res = get_anaf_invoices_handler({})
        self.assertEqual(res["status"], "success")
        self.assertIsInstance(res["invoices"], list)


if __name__ == "__main__":
    unittest.main()
