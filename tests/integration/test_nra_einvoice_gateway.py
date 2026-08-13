"""
Unit tests for NRA E-Invoice Portal Gateway (M60).
"""

import unittest
from datetime import datetime, timedelta

from src.integration.nra_einvoice_gateway import (
    QESCertificate,
    NRAAPICredentials,
    EInvoiceLineItem,
    NRAEInvoice,
    NRAEInvoicePortalGateway,
    InvoiceType,
    SubmissionStatus,
    InvoiceTarget,
    PortalEndpointStatus
)

class TestNRAEInvoiceGateway(unittest.TestCase):
    def setUp(self):
        # Setup credentials
        self.valid_qes = QESCertificate(
            subject_name="Test Company LTD",
            issuer_name="Trust Provider",
            serial_number="123456789",
            valid_from="2026-01-01T00:00:00Z",
            valid_to="2027-01-01T00:00:00Z",
            public_key="pub_key_mock",
            private_key="priv_key_mock"
        )
        
        self.expired_qes = QESCertificate(
            subject_name="Test Company LTD",
            issuer_name="Trust Provider",
            serial_number="987654321",
            valid_from="2024-01-01T00:00:00Z",
            valid_to="2025-01-01T00:00:00Z",
            public_key="pub_key_mock",
            private_key="priv_key_mock"
        )
        
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        past_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        self.valid_creds = NRAAPICredentials(
            api_key="valid-api-key-123",
            api_secret="secret-abc",
            environment="sandbox",
            expires_at=future_date
        )
        
        self.expired_creds = NRAAPICredentials(
            api_key="expired-api-key-123",
            api_secret="secret-abc",
            environment="sandbox",
            expires_at=past_date
        )
        
        self.gateway = NRAEInvoicePortalGateway(
            credentials=self.valid_creds,
            qes_certificate=self.valid_qes
        )

    def _create_sample_invoice(self, invoice_type=InvoiceType.INVOICE, target=InvoiceTarget.B2G):
        items = [
            EInvoiceLineItem(
                description="Consulting Services",
                quantity=10.0,
                unit_price=100.0,
                vat_rate=20.0
            ),
            EInvoiceLineItem(
                description="Software License",
                quantity=1.0,
                unit_price=500.0,
                vat_rate=20.0
            )
        ]
        return NRAEInvoice(
            invoice_number="INV-2026-0001",
            issue_date="2026-08-15",
            supplier_vat="BG123456789",
            supplier_name="Test Supplier Ltd",
            buyer_vat="BG987654321",
            buyer_name="Test Buyer Ltd",
            invoice_type=invoice_type,
            target=target,
            line_items=items
        )

    def test_qes_certificate_dataclass(self):
        self.assertEqual(self.valid_qes.subject_name, "Test Company LTD")
        self.assertEqual(self.valid_qes.serial_number, "123456789")
        self.assertIsNotNone(self.valid_qes.valid_from)

    def test_nra_api_credentials_dataclass(self):
        creds = NRAAPICredentials(api_key="key", api_secret="sec")
        self.assertEqual(creds.environment, "production")  # Assuming default is production
        self.assertIsInstance(creds, NRAAPICredentials)

    def test_einvoice_line_item_defaults(self):
        item = EInvoiceLineItem(description="Item 1", quantity=1.0, unit_price=10.0)
        self.assertEqual(item.vat_rate, 20.0)

    def test_nra_einvoice_computed_properties(self):
        invoice = self._create_sample_invoice()
        # 10 * 100 = 1000, 1 * 500 = 500 => Total 1500
        # VAT 20% => 300
        self.assertEqual(invoice.taxable_base, 1500.0)
        self.assertEqual(invoice.total_vat, 300.0)
        self.assertEqual(invoice.total_amount, 1800.0)

    def test_validate_qes_certificate_valid(self):
        is_valid = NRAEInvoicePortalGateway.validate_qes_certificate(self.valid_qes)
        self.assertTrue(is_valid)

    def test_validate_qes_certificate_expired(self):
        is_valid = NRAEInvoicePortalGateway.validate_qes_certificate(self.expired_qes)
        self.assertFalse(is_valid)

    def test_validate_api_key_freshness_valid(self):
        is_valid = NRAEInvoicePortalGateway.validate_api_key_freshness(self.valid_creds)
        self.assertTrue(is_valid)

    def test_validate_api_key_freshness_expired(self):
        is_valid = NRAEInvoicePortalGateway.validate_api_key_freshness(self.expired_creds)
        self.assertFalse(is_valid)

    def test_validate_invoice_en16931_valid(self):
        invoice = self._create_sample_invoice()
        errors = self.gateway.validate_invoice_en16931(invoice)
        self.assertEqual(len(errors), 0)

    def test_validate_invoice_en16931_missing_fields(self):
        invoice = self._create_sample_invoice()
        invoice.buyer_vat = ""
        errors = self.gateway.validate_invoice_en16931(invoice)
        self.assertGreater(len(errors), 0)
        self.assertIn("buyer_vat", errors[0])

    def test_generate_ubl_xml_structure(self):
        invoice = self._create_sample_invoice()
        xml_content = self.gateway.generate_ubl_xml(invoice)
        self.assertIn("<Invoice", xml_content)
        self.assertIn("<cbc:ID>INV-2026-0001</cbc:ID>", xml_content)
        self.assertIn("<cac:AccountingSupplierParty>", xml_content)
        self.assertIn("<cac:InvoiceLine>", xml_content)
        self.assertIn(">1500.00<", xml_content)  # Taxable base or similar
        
    def test_sign_invoice_qes(self):
        invoice = self._create_sample_invoice()
        xml_content = self.gateway.generate_ubl_xml(invoice)
        signature = self.gateway.sign_invoice_qes(xml_content, self.valid_qes)
        self.assertIsNotNone(signature)
        self.assertTrue(len(signature) > 10)

    def test_submit_b2g_invoice_success(self):
        invoice = self._create_sample_invoice(target=InvoiceTarget.B2G)
        result = self.gateway.submit_invoice(invoice)
        self.assertEqual(result.status, SubmissionStatus.SUBMITTED)
        self.assertIsNotNone(result.submission_id)

    def test_submit_b2b_invoice_success(self):
        invoice = self._create_sample_invoice(target=InvoiceTarget.B2B)
        result = self.gateway.submit_invoice(invoice)
        self.assertEqual(result.status, SubmissionStatus.SUBMITTED)
        self.assertIsNotNone(result.submission_id)

    def test_check_submission_status(self):
        status = self.gateway.check_submission_status("SUB-12345")
        self.assertIn(status, [SubmissionStatus.SUBMITTED, SubmissionStatus.ACCEPTED, SubmissionStatus.REJECTED])

    def test_batch_submit_invoices(self):
        invoices = [
            self._create_sample_invoice(),
            self._create_sample_invoice(),
            self._create_sample_invoice()
        ]
        results = self.gateway.batch_submit_invoices(invoices)
        self.assertEqual(len(results), 3)
        for res in results:
            self.assertEqual(res.status, SubmissionStatus.SUBMITTED)

    def test_check_portal_health(self):
        health_status = self.gateway.check_portal_health()
        self.assertIsInstance(health_status, dict)
        self.assertIn("api_endpoint", health_status)
        self.assertEqual(health_status["api_endpoint"], PortalEndpointStatus.ONLINE)

    def test_get_gateway_status(self):
        status = self.gateway.get_gateway_status()
        self.assertIn("environment", status)
        self.assertIn("qes_valid", status)
        self.assertTrue(status["qes_valid"])

    def test_submit_invoice_with_credit_note(self):
        invoice = self._create_sample_invoice(invoice_type=InvoiceType.CREDIT_NOTE)
        result = self.gateway.submit_invoice(invoice)
        self.assertEqual(result.status, SubmissionStatus.SUBMITTED)

    def test_einvoice_with_zero_vat_rate(self):
        invoice = self._create_sample_invoice()
        invoice.line_items[0].vat_rate = 0.0
        invoice.line_items[1].vat_rate = 0.0
        # Taxable base 1500, VAT 0
        self.assertEqual(invoice.taxable_base, 1500.0)
        self.assertEqual(invoice.total_vat, 0.0)
        self.assertEqual(invoice.total_amount, 1500.0)

if __name__ == '__main__':
    unittest.main()
