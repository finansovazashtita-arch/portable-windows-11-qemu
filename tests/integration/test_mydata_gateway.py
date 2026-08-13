"""
Tests for M80 Greece myDATA (AADE) Compliance Gateway.

Tests cover:
  1. AFM (ΑΦΜ) Mod-11 Check Digit Validation (valid & invalid AFMs).
  2. GreekParty Dataclass & clean_afm formatting.
  3. InvoiceLineItem & MyDATAInvoice totals calculations.
  4. myDATA InvoicesDoc XML Generation (namespaces, elements, attributes).
  5. Business Validation Rules (AFM check, positive net values, classification checks).
  6. MARK Identifier Generation & Registry Tracking.
  7. Income Invoice Submission (sendInvoices simulation & MARK assignment).
  8. Expense Classification Submission (sendExpensesClassification simulation).
  9. Document Cancellation (CancelInvoice by MARK).
 10. Greek Double-Entry Journal Entry Generation.
 11. REST API Handlers in src/integration/mydata_api.py.
"""

import unittest
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from src.integration.mydata_gateway import (
    GreekParty,
    InvoiceLineItem,
    MyDATAInvoice,
    MyDATAGateway,
    MyDATAEnvironment,
    InvoiceType,
    VATCategory,
    DocumentStatus,
    validate_afm,
)
from src.integration.mydata_api import (
    get_mydata_health_handler,
    post_mydata_afm_validate_handler,
    post_mydata_generate_xml_handler,
    post_mydata_send_invoices_handler,
    post_mydata_journal_entries_handler,
)


class TestAFMValidation(unittest.TestCase):
    """Test Greek AFM (ΑΦΜ) Mod-11 validation."""

    def test_valid_afms(self):
        valid_afms = [
            "094018881",   # Standard corporate AFM
            "800000000",   # Test AFM
            "123456789",   # Valid Mod-11 AFM
            "999999999",   # Test AFM
            "EL094018881",  # With country prefix
            " 094018881 ",  # With whitespace
        ]
        for afm in valid_afms:
            is_valid, clean_afm, msg = validate_afm(afm)
            self.assertTrue(is_valid, f"AFM {afm} should be valid: {msg}")
            self.assertEqual(len(clean_afm), 9)

    def test_invalid_afms(self):
        invalid_afms = [
            "123456780",     # Wrong check digit
            "123",           # Too short
            "123456789012",  # Too long
            "ABCDEFGHI",     # Non-numeric
            "",              # Empty
        ]
        for afm in invalid_afms:
            is_valid, clean_afm, msg = validate_afm(afm)
            self.assertFalse(is_valid, f"AFM {afm} should be invalid")


class TestMyDATAGatewayCore(unittest.TestCase):
    """Test MyDATAGateway core methods, XML building, and submission."""

    def setUp(self):
        self.gateway = MyDATAGateway(
            aade_user_id="TEST_USER",
            subscription_key="TEST_KEY",
            environment=MyDATAEnvironment.SANDBOX,
        )
        self.issuer = GreekParty(afm="094018881", name="ΕΛΛΗΝΙΚΗ ΕΤΑΙΡΕΙΑ Α.Ε.", country_code="GR")
        self.counterpart = GreekParty(afm="800000000", name="ΠΕΛΑΤΗΣ Ε.Π.Ε.", country_code="GR")

    def test_invoice_totals_calculation(self):
        line1 = InvoiceLineItem(
            line_number=1,
            net_value=1000.00,
            vat_category=VATCategory.RATE_24,
            vat_amount=240.00,
            income_classification_type="E3_561_001",
        )
        line2 = InvoiceLineItem(
            line_number=2,
            net_value=500.00,
            vat_category=VATCategory.RATE_13,
            vat_amount=65.00,
            income_classification_type="E3_561_001",
        )
        invoice = MyDATAInvoice(
            uid="INV-TEST-001",
            issuer=self.issuer,
            counterpart=self.counterpart,
            invoice_type=InvoiceType.SALES_INVOICE,
            issue_date="2026-08-13",
            lines=[line1, line2],
        )
        self.assertAlmostEqual(invoice.total_net_value, 1500.00)
        self.assertAlmostEqual(invoice.total_vat_amount, 305.00)
        self.assertAlmostEqual(invoice.total_gross_value, 1805.00)

    def test_xml_generation(self):
        line = InvoiceLineItem(
            line_number=1,
            net_value=100.00,
            vat_category=VATCategory.RATE_24,
            vat_amount=24.00,
            income_classification_type="E3_561_001",
        )
        invoice = MyDATAInvoice(
            uid="INV-XML-001",
            issuer=self.issuer,
            counterpart=self.counterpart,
            invoice_type=InvoiceType.SALES_INVOICE,
            issue_date="2026-08-13",
            lines=[line],
        )
        xml_str = self.gateway.build_invoices_xml([invoice])

        self.assertIn("InvoicesDoc", xml_str)
        self.assertIn("094018881", xml_str)
        self.assertIn("800000000", xml_str)

        # Parse XML to verify structural integrity
        root = ET.fromstring(xml_str)
        self.assertTrue(root.tag.endswith("InvoicesDoc"))

    def test_invoice_validation(self):
        # Valid invoice
        line = InvoiceLineItem(
            line_number=1,
            net_value=100.00,
            vat_category=VATCategory.RATE_24,
            vat_amount=24.00,
        )
        inv = MyDATAInvoice(
            uid="INV-VAL-001",
            issuer=self.issuer,
            invoice_type=InvoiceType.SALES_INVOICE,
            issue_date="2026-08-13",
            lines=[line],
        )
        val = self.gateway.validate_invoice(inv)
        self.assertTrue(val["valid"])

        # Invalid invoice (invalid issuer AFM)
        inv_bad_afm = MyDATAInvoice(
            uid="INV-VAL-BAD",
            issuer=GreekParty(afm="123456780", name="Bad AFM Inc"),
            invoice_type=InvoiceType.SALES_INVOICE,
            issue_date="2026-08-13",
            lines=[line],
        )
        val_bad = self.gateway.validate_invoice(inv_bad_afm)
        self.assertFalse(val_bad["valid"])

    def test_send_invoices_and_mark_generation(self):
        line = InvoiceLineItem(
            line_number=1,
            net_value=200.00,
            vat_category=VATCategory.RATE_24,
            vat_amount=48.00,
        )
        inv = MyDATAInvoice(
            uid="INV-SEND-001",
            issuer=self.issuer,
            invoice_type=InvoiceType.SALES_INVOICE,
            issue_date="2026-08-13",
            lines=[line],
        )
        result = self.gateway.send_invoices([inv])
        self.assertTrue(result["success"])
        self.assertEqual(result["submitted"], 1)
        self.assertIsNotNone(inv.mark)
        self.assertEqual(inv.status, DocumentStatus.ACCEPTED)

    def test_cancel_invoice(self):
        line = InvoiceLineItem(line_number=1, net_value=100.00, vat_category=VATCategory.RATE_24, vat_amount=24.00)
        inv = MyDATAInvoice(
            uid="INV-CANCEL-001",
            issuer=self.issuer,
            invoice_type=InvoiceType.SALES_INVOICE,
            issue_date="2026-08-13",
            lines=[line],
        )
        self.gateway.send_invoices([inv])

        cancel_res = self.gateway.cancel_invoice(inv.mark)
        self.assertTrue(cancel_res["success"])
        self.assertIsNotNone(cancel_res["cancellation_mark"])

    def test_journal_entries_generation(self):
        line = InvoiceLineItem(line_number=1, net_value=1000.00, vat_category=VATCategory.RATE_24, vat_amount=240.00)
        inv = MyDATAInvoice(
            uid="INV-JNL-001",
            issuer=self.issuer,
            invoice_type=InvoiceType.SALES_INVOICE,
            issue_date="2026-08-13",
            lines=[line],
        )

        entries = self.gateway.generate_journal_entries(inv)
        total_debit = sum(e["debit"] for e in entries)
        total_credit = sum(e["credit"] for e in entries)

        self.assertAlmostEqual(total_debit, 1240.00)
        self.assertAlmostEqual(total_credit, 1240.00)


class TestMyDATAAPIHandlers(unittest.TestCase):
    """Test REST API handlers defined in src/integration/mydata_api.py."""

    def test_health_handler(self):
        res = get_mydata_health_handler({})
        self.assertEqual(res["status"], "ONLINE")

    def test_afm_validate_handler(self):
        res = post_mydata_afm_validate_handler({"afm": "094018881"})
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["valid"])

    def test_generate_xml_handler(self):
        payload = {
            "issuer": {"afm": "094018881", "name": "ΕΤΑΙΡΕΙΑ A.E."},
            "invoice_type": "1.1",
            "issue_date": "2026-08-13",
            "series": "A",
            "aa": "101",
            "lines": [{"line_number": 1, "net_value": 500.0, "vat_category": "1", "vat_amount": 120.0}]
        }
        res = post_mydata_generate_xml_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertIn("xml_content", res)

    def test_send_invoices_handler(self):
        payload = {
            "issuer": {"afm": "094018881", "name": "ΕΤΑΙΡΕΙΑ A.E."},
            "invoice_type": "1.1",
            "issue_date": "2026-08-13",
            "lines": [{"line_number": 1, "net_value": 300.0, "vat_category": "1", "vat_amount": 72.0}]
        }
        res = post_mydata_send_invoices_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["submitted"], 1)

    def test_journal_entries_handler(self):
        payload = {
            "issuer": {"afm": "094018881", "name": "ΕΤΑΙΡΕΙΑ A.E."},
            "invoice_type": "1.1",
            "issue_date": "2026-08-13",
            "lines": [{"line_number": 1, "net_value": 1000.0, "vat_category": "1", "vat_amount": 240.0}]
        }
        res = post_mydata_journal_entries_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["totals"]["balanced"])


if __name__ == "__main__":
    unittest.main()
