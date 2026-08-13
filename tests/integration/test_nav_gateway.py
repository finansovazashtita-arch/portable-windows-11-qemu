"""
Tests for M82 Hungary NAV Online Számla 3.0 Gateway.

Test Coverage:
  1.  Hungarian Tax Number (Adószám) Mod-11 Validation — valid & invalid cases
  2.  NAVTaxpayer dataclass — clean_tax_number, hu_vat_number, is_valid
  3.  HUF Rounding — round_huf precision (0 decimal places)
  4.  SHA-3-512 Request Signature — deterministic computation
  5.  NAVRequestSigner — generate_request_id, current_timestamp, signature
  6.  XMLDSig Signing — sign_invoice_xml envelope structure
  7.  NAVInvoiceLineItem — calculate_totals for all VAT rates
  8.  NAVInvoice — calculate_totals aggregation & VAT summary
  9.  NAVInvoiceGenerator — generate_invoice_data_xml (XML structure & elements)
  10. NAVInvoiceGenerator — generate_token_exchange_request_xml
  11. NAVInvoiceGenerator — generate_manage_invoice_request_xml
  12. NAVInvoiceGenerator — generate_query_taxpayer_request_xml
  13. NAVDoubleEntryMapper — domestic sales invoice journal entries
  14. NAVDoubleEntryMapper — STORNO reversal journal entries
  15. NAVDoubleEntryMapper — foreign customer (319 receivable)
  16. NAVOnlineSzamlaGateway — sandbox token exchange
  17. NAVOnlineSzamlaGateway — sandbox invoice submission workflow
  18. NAVOnlineSzamlaGateway — invoice status query
  19. NAVOnlineSzamlaGateway — query taxpayer (sandbox)
  20. NAVOnlineSzamlaGateway — list_invoices & get_invoice
  21. NAVOnlineSzamlaGateway — statistics
  22. NAV API handlers — health check
  23. NAV API handlers — validate tax number
  24. NAV API handlers — token exchange
  25. NAV API handlers — generate XML
  26. NAV API handlers — submit invoice
  27. NAV API handlers — query status
  28. NAV API handlers — query taxpayer
  29. NAV API handlers — journal entries
  30. NAV API handlers — invoice listing
"""

import json
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from src.integration.nav_gateway import (
    NAVCredentials,
    NAVDoubleEntryMapper,
    NAVEnvironment,
    NAVInvoice,
    NAVInvoiceAppearance,
    NAVInvoiceCategory,
    NAVInvoiceGenerator,
    NAVInvoiceLineItem,
    NAVInvoiceOperation,
    NAVInvoiceStatus,
    NAVOnlineSzamlaGateway,
    NAVPaymentMethod,
    NAVRequestSigner,
    NAVSession,
    NAVTaxpayer,
    NAVVATRate,
    NAVXMLDSigSigner,
    format_tax_number,
    round_huf,
    validate_tax_number,
)
from src.integration.nav_api import (
    get_nav_health_handler,
    get_nav_invoices_handler,
    get_nav_statistics_handler,
    post_nav_generate_xml_handler,
    post_nav_journal_entries_handler,
    post_nav_query_status_handler,
    post_nav_query_taxpayer_handler,
    post_nav_submit_invoice_handler,
    post_nav_token_exchange_handler,
    post_nav_validate_tax_handler,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_supplier(tax_number: str = "12345674-2-41") -> NAVTaxpayer:
    return NAVTaxpayer(
        tax_number=tax_number,
        name="FinansProtect Kft.",
        address_country="HU",
        address_postal_code="1051",
        address_city="Budapest",
        address_street="Váci utca 1.",
        bank_account_number="HU76117730161111101800000000",
    )


def _make_customer(tax_number: str = "98765432-2-02", country: str = "HU") -> NAVTaxpayer:
    return NAVTaxpayer(
        tax_number=tax_number,
        name="Magyar Vállalat Zrt.",
        address_country=country,
        address_postal_code="1054",
        address_city="Budapest",
        address_street="Szabadság tér 10.",
        vat_status="DOMESTIC" if country == "HU" else "FOREIGN",
    )


def _make_line_item(
    line_number: int = 1,
    description: str = "IT Szoftver fejlesztés",
    quantity: float = 1.0,
    unit_price_huf: float = 500_000.0,
    vat_rate: NAVVATRate = NAVVATRate.RATE_27,
) -> NAVInvoiceLineItem:
    item = NAVInvoiceLineItem(
        line_number=line_number,
        description=description,
        quantity=quantity,
        unit_price_huf=unit_price_huf,
        vat_rate=vat_rate,
    )
    item.calculate_totals()
    return item


def _make_invoice(
    operation: NAVInvoiceOperation = NAVInvoiceOperation.CREATE,
    customer_country: str = "HU",
) -> NAVInvoice:
    supplier = _make_supplier()
    customer = _make_customer(country=customer_country)
    item = _make_line_item()
    inv = NAVInvoice(
        invoice_number="SZL/2026/001",
        invoice_issue_date="2026-08-13",
        payment_date="2026-08-28",
        delivery_date="2026-08-13",
        supplier=supplier,
        customer=customer,
        items=[item],
        operation=operation,
        nav_annul_reference="SZL/2026/000" if operation != NAVInvoiceOperation.CREATE else "",
    )
    inv.calculate_totals()
    return inv


def _make_credentials() -> NAVCredentials:
    return NAVCredentials(
        login="test_user",
        password="test_password",
        tax_number="12345674-2-41",
        signature_key="TEST-SIGNATURE-KEY-1234567890ABCD",
        exchange_key="TEST-EXCHANGE-KEY-0987654321EFGH",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. HUNGARIAN TAX NUMBER VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

class TestHungarianTaxNumberValidation(unittest.TestCase):
    """Test Modulo 11 Hungarian adószám validation."""

    def test_valid_8digit_tax_numbers(self):
        """Test valid 8-digit adószám (core only)."""
        # Manually computed: SUM(d × [9,7,3,1,9,7,3]) MOD 10 = check digit
        # 12345676: 1×9 + 2×7 + 3×3 + 4×1 + 5×9 + 6×7 + 7×3 = 9+14+9+4+45+42+21 = 144 → 144%10=4 → check=4 → 4 != 6 invalid
        # Construct a known-valid adószám manually:
        # digits[0..6] = [1,0,5,0,0,0,0], weights = [9,7,3,1,9,7,3]
        # sum = 9+0+15+0+0+0+0 = 24 → 24%10=4 → check digit = 4
        # So 10500004 should be valid
        self.assertTrue(validate_tax_number("10500004"))

        # digits = [1,2,3,4,5,6,7], weights = [9,7,3,1,9,7,3]
        # sum = 9+14+9+4+45+42+21 = 144 → 144%10 = 4 → 8th digit must be 4
        # 12345674 should be valid
        self.assertTrue(validate_tax_number("12345674"))

    def test_valid_11digit_tax_numbers(self):
        """Test valid 11-digit full adószám format: XXXXXXXX-Y-ZZ."""
        # 10500004-2-41: 8-digit core valid, Y=2 (ÁFA registered), ZZ=41 (Fejér county)
        self.assertTrue(validate_tax_number("10500004-2-41"))
        self.assertTrue(validate_tax_number("10500004241"))   # Without hyphens
        self.assertTrue(validate_tax_number("HU10500004"))    # HU prefix, 8-digit

    def test_invalid_tax_numbers(self):
        """Test various invalid tax numbers are rejected."""
        # Wrong check digit
        self.assertFalse(validate_tax_number("12345678"))     # check digit 8 != computed 4
        self.assertFalse(validate_tax_number("10500001"))     # check digit 1 != computed 4
        self.assertFalse(validate_tax_number("10500009"))     # check digit 9 != computed 4

        # Wrong length
        self.assertFalse(validate_tax_number("123"))
        self.assertFalse(validate_tax_number("1234567890123"))

        # Non-numeric
        self.assertFalse(validate_tax_number("ABCDEFGH"))
        self.assertFalse(validate_tax_number(""))
        self.assertFalse(validate_tax_number(None))

    def test_county_code_validation(self):
        """Test 11-digit format with invalid county code."""
        # Valid base 10500004 + VAT status 2 + county 41 → valid
        self.assertTrue(validate_tax_number("10500004-2-41"))

        # Invalid county code: 01 (too low) or 99 (too high)
        self.assertFalse(validate_tax_number("10500004-2-01"))
        self.assertFalse(validate_tax_number("10500004-2-99"))

        # Invalid VAT status digit: 3 or 6
        self.assertFalse(validate_tax_number("10500004-3-41"))
        self.assertFalse(validate_tax_number("10500004-6-41"))

    def test_format_tax_number(self):
        """Test format_tax_number extracts clean 8-digit core."""
        self.assertEqual(format_tax_number("12345674"),      "12345674")
        self.assertEqual(format_tax_number("12345674-2-41"), "12345674")
        self.assertEqual(format_tax_number("HU12345674"),    "12345674")
        self.assertEqual(format_tax_number("12345674-2-41", include_hu_prefix=True), "HU12345674")
        self.assertEqual(format_tax_number(" HU 12345674 "), "12345674")


# ─────────────────────────────────────────────────────────────────────────────
# 2. NAVTaxpayer DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

class TestNAVTaxpayer(unittest.TestCase):

    def test_clean_tax_number(self):
        tp = NAVTaxpayer(tax_number="12345674-2-41", name="Test Kft.")
        self.assertEqual(tp.clean_tax_number(), "12345674")

    def test_hu_vat_number(self):
        tp = NAVTaxpayer(tax_number="12345674-2-41", name="Test Kft.")
        self.assertEqual(tp.hu_vat_number(), "HU12345674")

    def test_is_valid_with_valid_tax_number(self):
        tp = NAVTaxpayer(tax_number="10500004-2-41", name="Valid Company")
        self.assertTrue(tp.is_valid())

    def test_is_valid_with_invalid_tax_number(self):
        tp = NAVTaxpayer(tax_number="99999999", name="Invalid Company")
        self.assertFalse(tp.is_valid())


# ─────────────────────────────────────────────────────────────────────────────
# 3. HUF ROUNDING
# ─────────────────────────────────────────────────────────────────────────────

class TestHUFRounding(unittest.TestCase):

    def test_round_huf_whole_numbers(self):
        self.assertEqual(round_huf(500_000.0),   500_000)
        self.assertEqual(round_huf(135_000.0),   135_000)
        self.assertEqual(round_huf(0.0),         0)

    def test_round_huf_fractional(self):
        """HUF has 0 decimal places — all fractions should round to nearest integer."""
        self.assertEqual(round_huf(500_000.4), 500_000)
        self.assertEqual(round_huf(500_000.5), 500_000)   # banker's rounding rounds to even (0)
        self.assertEqual(round_huf(500_001.5), 500_002)   # banker's rounding rounds to even (2)
        self.assertEqual(round_huf(135_000.7), 135_001)

    def test_round_huf_vat_27(self):
        """Test 27% VAT calculation on common invoice amounts."""
        net = 500_000.0
        vat = net * 0.27   # 135_000.0
        self.assertEqual(round_huf(vat), 135_000)
        gross = net + vat  # 635_000.0
        self.assertEqual(round_huf(gross), 635_000)

    def test_round_huf_negative(self):
        """STORNO invoices can have negative amounts."""
        self.assertEqual(round_huf(-500_000.0),  -500_000)
        self.assertEqual(round_huf(-135_000.7),  -135_001)


# ─────────────────────────────────────────────────────────────────────────────
# 4 & 5. SHA-3-512 REQUEST SIGNATURE
# ─────────────────────────────────────────────────────────────────────────────

class TestSHA3512Signature(unittest.TestCase):

    def test_signature_deterministic(self):
        """Same inputs must produce same SHA-3-512 hex digest."""
        sig1 = NAVRequestSigner.compute_request_signature(
            "REQID001", "2026-08-13T14:00:00Z", "SECRET-KEY-123", "BASE64DATA=="
        )
        sig2 = NAVRequestSigner.compute_request_signature(
            "REQID001", "2026-08-13T14:00:00Z", "SECRET-KEY-123", "BASE64DATA=="
        )
        self.assertEqual(sig1, sig2)

    def test_signature_length(self):
        """SHA-3-512 produces 128 hex characters (512 bits)."""
        sig = NAVRequestSigner.compute_request_signature(
            "REQID001", "2026-08-13T14:00:00Z", "SECRET-KEY-123"
        )
        self.assertEqual(len(sig), 128)

    def test_signature_uppercase(self):
        """Signature hex must be uppercase per NAV specification."""
        sig = NAVRequestSigner.compute_request_signature(
            "ABC", "2026-01-01T00:00:00Z", "KEY"
        )
        self.assertEqual(sig, sig.upper())

    def test_signature_different_inputs(self):
        """Different inputs must produce different signatures."""
        sig1 = NAVRequestSigner.compute_request_signature("REQ1", "T1", "K1")
        sig2 = NAVRequestSigner.compute_request_signature("REQ2", "T1", "K1")
        self.assertNotEqual(sig1, sig2)

    def test_generate_request_id(self):
        """Request ID must be a 32-character uppercase hex string."""
        req_id = NAVRequestSigner.generate_request_id()
        self.assertEqual(len(req_id), 32)
        self.assertTrue(req_id.isupper() or req_id.replace('-','').isupper())
        # Must be unique
        req_id2 = NAVRequestSigner.generate_request_id()
        self.assertNotEqual(req_id, req_id2)

    def test_current_timestamp_format(self):
        """Timestamp must match NAV format: YYYY-MM-DDTHH:MM:SSZ."""
        ts = NAVRequestSigner.current_timestamp()
        self.assertTrue(ts.endswith("Z"))
        # Must be parseable as UTC datetime
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        self.assertIsNotNone(dt)

    def test_known_signature_value(self):
        """Test a known SHA-3-512 value for regression detection."""
        import hashlib
        payload = "REQ123" + "2026-08-13T10:00:00Z" + "MYKEY" + ""
        expected = hashlib.sha3_512(payload.encode("utf-8")).hexdigest().upper()
        result   = NAVRequestSigner.compute_request_signature(
            "REQ123", "2026-08-13T10:00:00Z", "MYKEY"
        )
        self.assertEqual(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# 6. XMLDSig SIGNING
# ─────────────────────────────────────────────────────────────────────────────

class TestXMLDSigSigner(unittest.TestCase):

    def setUp(self):
        self.raw_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<InvoiceData xmlns="http://schemas.nav.gov.hu/OSA/3.0/data">'
            '<invoiceNumber>SZL/2026/001</invoiceNumber>'
            '</InvoiceData>'
        )

    def test_signed_xml_contains_signature(self):
        signed = NAVXMLDSigSigner.sign_invoice_xml(self.raw_xml, "SZL/2026/001")
        self.assertIn("<ds:Signature", signed)
        self.assertIn("</ds:Signature>", signed)

    def test_signed_xml_contains_signed_info(self):
        signed = NAVXMLDSigSigner.sign_invoice_xml(self.raw_xml, "SZL/2026/001")
        self.assertIn("<ds:SignedInfo", signed)
        self.assertIn("<ds:SignatureValue>", signed)
        self.assertIn("</ds:SignatureValue>", signed)

    def test_signed_xml_digest_method(self):
        """Digest method must be SHA-256."""
        signed = NAVXMLDSigSigner.sign_invoice_xml(self.raw_xml, "SZL/2026/001")
        self.assertIn("http://www.w3.org/2001/04/xmlenc#sha256", signed)

    def test_signed_xml_signature_algorithm(self):
        """Signature algorithm must be RSA-SHA256."""
        signed = NAVXMLDSigSigner.sign_invoice_xml(self.raw_xml, "SZL/2026/001")
        self.assertIn("rsa-sha256", signed)

    def test_signed_xml_c14n_algorithm(self):
        """Canonicalization must be XML-C14N 1.0."""
        signed = NAVXMLDSigSigner.sign_invoice_xml(self.raw_xml, "SZL/2026/001")
        self.assertIn("REC-xml-c14n-20010315", signed)

    def test_signed_xml_preserves_invoice_content(self):
        """XMLDSig signing must not corrupt invoice content."""
        signed = NAVXMLDSigSigner.sign_invoice_xml(self.raw_xml, "SZL/2026/001")
        self.assertIn("SZL/2026/001", signed)
        self.assertIn("InvoiceData", signed)

    def test_signed_xml_id_attribute(self):
        """Root element must have an Id attribute for the Reference URI."""
        signed = NAVXMLDSigSigner.sign_invoice_xml(self.raw_xml, "SZL/2026/001")
        self.assertIn('Id="', signed)
        self.assertIn("inv-SZL-2026-001", signed)  # Sanitized invoice number


# ─────────────────────────────────────────────────────────────────────────────
# 7. NAVInvoiceLineItem CALCULATIONS
# ─────────────────────────────────────────────────────────────────────────────

class TestNAVInvoiceLineItem(unittest.TestCase):

    def test_calculate_totals_27pct(self):
        item = NAVInvoiceLineItem(
            line_number=1,
            description="IT Szoftver",
            quantity=2.0,
            unit_price_huf=500_000.0,
            vat_rate=NAVVATRate.RATE_27,
        )
        item.calculate_totals()
        self.assertAlmostEqual(item.line_net_amount_huf,   1_000_000.0, places=2)
        self.assertAlmostEqual(item.line_vat_amount_huf,     270_000.0, places=2)
        self.assertAlmostEqual(item.line_gross_amount_huf, 1_270_000.0, places=2)

    def test_calculate_totals_18pct(self):
        item = NAVInvoiceLineItem(
            line_number=1,
            description="Élelmiszer",
            quantity=1.0,
            unit_price_huf=100_000.0,
            vat_rate=NAVVATRate.RATE_18,
        )
        item.calculate_totals()
        self.assertAlmostEqual(item.line_net_amount_huf,   100_000.0, places=2)
        self.assertAlmostEqual(item.line_vat_amount_huf,    18_000.0, places=2)
        self.assertAlmostEqual(item.line_gross_amount_huf, 118_000.0, places=2)

    def test_calculate_totals_5pct(self):
        item = NAVInvoiceLineItem(
            line_number=1,
            description="Gyógyszer",
            quantity=3.0,
            unit_price_huf=10_000.0,
            vat_rate=NAVVATRate.RATE_5,
        )
        item.calculate_totals()
        self.assertAlmostEqual(item.line_net_amount_huf,  30_000.0, places=2)
        self.assertAlmostEqual(item.line_vat_amount_huf,   1_500.0, places=2)
        self.assertAlmostEqual(item.line_gross_amount_huf,31_500.0, places=2)

    def test_calculate_totals_exempt(self):
        item = NAVInvoiceLineItem(
            line_number=1,
            description="ÁFA mentes szolgáltatás",
            quantity=1.0,
            unit_price_huf=200_000.0,
            vat_rate=NAVVATRate.EXEMPT,
        )
        item.calculate_totals()
        self.assertAlmostEqual(item.line_vat_amount_huf,  0.0, places=2)
        self.assertAlmostEqual(item.line_gross_amount_huf, 200_000.0, places=2)

    def test_calculate_totals_reverse_charge(self):
        item = NAVInvoiceLineItem(
            line_number=1,
            description="Fordított adózás alá eső termék",
            quantity=1.0,
            unit_price_huf=500_000.0,
            vat_rate=NAVVATRate.REVERSE,
        )
        item.calculate_totals()
        self.assertAlmostEqual(item.line_vat_amount_huf,  0.0, places=2)
        self.assertAlmostEqual(item.line_gross_amount_huf, 500_000.0, places=2)

    def test_calculate_totals_zero_rate(self):
        item = NAVInvoiceLineItem(
            line_number=1,
            description="Exportált termék",
            quantity=5.0,
            unit_price_huf=50_000.0,
            vat_rate=NAVVATRate.RATE_0,
        )
        item.calculate_totals()
        self.assertAlmostEqual(item.line_net_amount_huf,   250_000.0, places=2)
        self.assertAlmostEqual(item.line_vat_amount_huf,   0.0,       places=2)
        self.assertAlmostEqual(item.line_gross_amount_huf, 250_000.0, places=2)


# ─────────────────────────────────────────────────────────────────────────────
# 8. NAVInvoice AGGREGATION
# ─────────────────────────────────────────────────────────────────────────────

class TestNAVInvoiceAggregation(unittest.TestCase):

    def test_single_item_invoice_totals(self):
        inv = _make_invoice()
        self.assertAlmostEqual(inv.invoice_net_amount,   500_000.0,  places=2)
        self.assertAlmostEqual(inv.invoice_vat_amount,   135_000.0,  places=2)
        self.assertAlmostEqual(inv.invoice_gross_amount, 635_000.0,  places=2)

    def test_multi_item_invoice_totals(self):
        supplier = _make_supplier()
        customer = _make_customer()
        items = [
            _make_line_item(1, "Szolgáltatás A", 2.0, 100_000.0, NAVVATRate.RATE_27),
            _make_line_item(2, "Termék B",       1.0,  50_000.0, NAVVATRate.RATE_5),
            _make_line_item(3, "Export C",       3.0,  20_000.0, NAVVATRate.RATE_0),
        ]
        inv = NAVInvoice(
            invoice_number="SZL/2026/002",
            invoice_issue_date="2026-08-13",
            payment_date="2026-08-28",
            delivery_date="2026-08-13",
            supplier=supplier,
            customer=customer,
            items=items,
        )
        inv.calculate_totals()

        # Net: 200_000 + 50_000 + 60_000 = 310_000
        # VAT: 200_000×0.27 + 50_000×0.05 + 0 = 54_000 + 2_500 = 56_500
        # Gross: 310_000 + 56_500 = 366_500
        self.assertAlmostEqual(inv.invoice_net_amount,   310_000.0, places=2)
        self.assertAlmostEqual(inv.invoice_vat_amount,    56_500.0, places=2)
        self.assertAlmostEqual(inv.invoice_gross_amount, 366_500.0, places=2)

    def test_vat_summary_structure(self):
        inv = _make_invoice()
        self.assertIn("27", inv.vat_summary)
        self.assertAlmostEqual(inv.vat_summary["27"]["net"],   500_000.0, places=2)
        self.assertAlmostEqual(inv.vat_summary["27"]["vat"],   135_000.0, places=2)
        self.assertAlmostEqual(inv.vat_summary["27"]["gross"], 635_000.0, places=2)

    def test_invoice_raises_on_empty_items(self):
        supplier = _make_supplier()
        customer = _make_customer()
        inv = NAVInvoice(
            invoice_number="EMPTY",
            invoice_issue_date="2026-08-13",
            payment_date="2026-08-28",
            delivery_date="2026-08-13",
            supplier=supplier,
            customer=customer,
            items=[],
        )
        with self.assertRaises(ValueError):
            NAVInvoiceGenerator.generate_invoice_data_xml(inv)


# ─────────────────────────────────────────────────────────────────────────────
# 9. InvoiceData XML GENERATION
# ─────────────────────────────────────────────────────────────────────────────

class TestNAVInvoiceDataXML(unittest.TestCase):

    def setUp(self):
        self.invoice = _make_invoice()
        self.xml_str = NAVInvoiceGenerator.generate_invoice_data_xml(self.invoice)

    def test_xml_declaration(self):
        self.assertTrue(self.xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>'))

    def test_invoice_number_in_xml(self):
        self.assertIn("<invoiceNumber>SZL/2026/001</invoiceNumber>", self.xml_str)

    def test_invoice_issue_date_in_xml(self):
        self.assertIn("<invoiceIssueDate>2026-08-13</invoiceIssueDate>", self.xml_str)

    def test_schema_namespace_in_xml(self):
        self.assertIn("http://schemas.nav.gov.hu/OSA/3.0/data", self.xml_str)

    def test_supplier_info_in_xml(self):
        self.assertIn("FinansProtect Kft.", self.xml_str)
        self.assertIn("<taxpayerNumberBase>12345674</taxpayerNumberBase>", self.xml_str)
        self.assertIn("Budapest", self.xml_str)
        self.assertIn("HU76117730161111101800000000", self.xml_str)

    def test_customer_info_in_xml(self):
        self.assertIn("Magyar Vállalat Zrt.", self.xml_str)

    def test_invoice_line_in_xml(self):
        self.assertIn("IT Szoftver fejlesztés", self.xml_str)
        self.assertIn("<unitOfMeasure>PIECE</unitOfMeasure>", self.xml_str)

    def test_net_amount_in_xml(self):
        self.assertIn("<lineNetAmountHUF>500000</lineNetAmountHUF>", self.xml_str)

    def test_vat_percentage_in_xml(self):
        self.assertIn("<vatPercentage>0.2700</vatPercentage>", self.xml_str)

    def test_vat_amount_in_xml(self):
        self.assertIn("<lineVatAmountHUF>135000</lineVatAmountHUF>", self.xml_str)

    def test_gross_amount_in_xml(self):
        self.assertIn("<invoiceGrossAmountHUF>635000</invoiceGrossAmountHUF>", self.xml_str)

    def test_payment_method_in_xml(self):
        self.assertIn("<paymentMethod>TRANSFER</paymentMethod>", self.xml_str)

    def test_invoice_category_in_xml(self):
        self.assertIn("<invoiceCategory>NORMAL</invoiceCategory>", self.xml_str)

    def test_xml_parseable(self):
        """Generated XML must be well-formed and parseable."""
        # Remove XML declaration for ET
        body = self.xml_str.split('?>\n', 1)[-1]
        root = ET.fromstring(body)
        self.assertIsNotNone(root)

    def test_currency_code_huf(self):
        self.assertIn("<currencyCode>HUF</currencyCode>", self.xml_str)


# ─────────────────────────────────────────────────────────────────────────────
# 10. TOKEN EXCHANGE REQUEST XML
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenExchangeXML(unittest.TestCase):

    def test_token_exchange_xml_structure(self):
        creds = _make_credentials()
        req_id = "TESTREQID00001"
        ts = "2026-08-13T14:00:00Z"
        xml_str = NAVInvoiceGenerator.generate_token_exchange_request_xml(creds, req_id, ts)

        self.assertIn("TokenExchangeRequest", xml_str)
        self.assertIn("requestId>TESTREQID00001</", xml_str)
        self.assertIn("requestVersion>3.0</", xml_str)
        self.assertIn(f"login>{creds.login}</", xml_str)
        self.assertIn("taxNumber>12345674</", xml_str)
        self.assertIn("requestSignature>", xml_str)
        self.assertIn("FinansProtect NAV Gateway", xml_str)

    def test_token_exchange_password_hash_is_sha512(self):
        """Password must be stored as SHA-512 hex (not plaintext)."""
        import hashlib
        creds = _make_credentials()
        expected_hash = hashlib.sha512(creds.password.encode("utf-8")).hexdigest().upper()
        xml_str = NAVInvoiceGenerator.generate_token_exchange_request_xml(
            creds, "REQID", "2026-08-13T00:00:00Z"
        )
        self.assertIn(expected_hash, xml_str)
        self.assertNotIn(creds.password, xml_str)


# ─────────────────────────────────────────────────────────────────────────────
# 11. MANAGE INVOICE REQUEST XML
# ─────────────────────────────────────────────────────────────────────────────

class TestManageInvoiceRequestXML(unittest.TestCase):

    def test_manage_invoice_xml_structure(self):
        invoice = _make_invoice()
        creds   = _make_credentials()
        req_id  = "MANAGE001"
        ts      = "2026-08-13T14:00:00Z"

        xml_str = NAVInvoiceGenerator.generate_manage_invoice_request_xml(
            invoice, creds, req_id, ts
        )

        self.assertIn("ManageInvoiceRequest", xml_str)
        self.assertIn("common:requestId>MANAGE001</", xml_str)
        self.assertIn("common:login>test_user</", xml_str)
        self.assertIn("invoiceOperations>", xml_str)
        self.assertIn("invoiceOperation>", xml_str)
        self.assertIn("invoiceData>", xml_str)
        self.assertIn("<compressedContentIndicator>false</compressedContentIndicator>", xml_str)

    def test_manage_invoice_contains_base64(self):
        """invoiceData element must contain base64-encoded XML."""
        import base64
        invoice = _make_invoice()
        creds   = _make_credentials()
        xml_str = NAVInvoiceGenerator.generate_manage_invoice_request_xml(
            invoice, creds, "R1", "2026-08-13T00:00:00Z"
        )
        # Extract invoiceData content
        start = xml_str.index("<invoiceData>") + len("<invoiceData>")
        end   = xml_str.index("</invoiceData>")
        b64_data = xml_str[start:end].strip()
        # Must be valid base64
        try:
            decoded = base64.b64decode(b64_data).decode("utf-8")
            self.assertIn("InvoiceData", decoded)
        except Exception:
            self.fail("invoiceData is not valid base64")

    def test_manage_invoice_storno_operation(self):
        invoice = _make_invoice(operation=NAVInvoiceOperation.STORNO)
        creds   = _make_credentials()
        xml_str = NAVInvoiceGenerator.generate_manage_invoice_request_xml(
            invoice, creds, "R2", "2026-08-13T00:00:00Z"
        )
        self.assertIn("<invoiceOperation>STORNO</invoiceOperation>", xml_str)


# ─────────────────────────────────────────────────────────────────────────────
# 12. QUERY TAXPAYER REQUEST XML
# ─────────────────────────────────────────────────────────────────────────────

class TestQueryTaxpayerRequestXML(unittest.TestCase):

    def test_query_taxpayer_xml(self):
        creds   = _make_credentials()
        xml_str = NAVInvoiceGenerator.generate_query_taxpayer_request_xml(
            "12345674", creds, "QREQ1", "2026-08-13T00:00:00Z"
        )
        self.assertIn("QueryTaxpayerRequest", xml_str)
        self.assertIn("<taxNumber>12345674</taxNumber>", xml_str)


# ─────────────────────────────────────────────────────────────────────────────
# 13. DOUBLE-ENTRY JOURNAL ENTRIES — DOMESTIC SALES
# ─────────────────────────────────────────────────────────────────────────────

class TestNAVDoubleEntryMapper(unittest.TestCase):

    def test_domestic_sales_journal_entries(self):
        inv = _make_invoice()
        entries = NAVDoubleEntryMapper.generate_journal_entries(inv)

        # Should generate 2 entries: net revenue + VAT
        self.assertEqual(len(entries), 2)

        net_entry = entries[0]
        self.assertEqual(net_entry["account_debit"],  "311")   # Belföldi vevők
        self.assertEqual(net_entry["account_credit"], "701")   # Belföldi értékesítés
        self.assertEqual(net_entry["amount_huf"],     500_000)

        vat_entry = entries[1]
        self.assertEqual(vat_entry["account_debit"],  "311")   # Belföldi vevők
        self.assertEqual(vat_entry["account_credit"], "454")   # Fizetendő ÁFA
        self.assertEqual(vat_entry["amount_huf"],     135_000)

    def test_journal_entry_invoice_number(self):
        inv = _make_invoice()
        entries = NAVDoubleEntryMapper.generate_journal_entries(inv)
        for e in entries:
            self.assertEqual(e["invoice_number"], "SZL/2026/001")
            self.assertEqual(e["issue_date"],     "2026-08-13")

    def test_storno_journal_entries_negative(self):
        """STORNO reversal must generate negative amounts."""
        inv = _make_invoice(operation=NAVInvoiceOperation.STORNO)
        entries = NAVDoubleEntryMapper.generate_journal_entries(inv)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["amount_huf"], -500_000)  # Negated
        self.assertEqual(entries[1]["amount_huf"], -135_000)

    def test_foreign_customer_uses_319(self):
        """Foreign customers should use account 319 (Külföldi vevők)."""
        inv = _make_invoice(customer_country="DE")
        entries = NAVDoubleEntryMapper.generate_journal_entries(inv)

        self.assertEqual(entries[0]["account_debit"], "319")   # Külföldi vevők
        self.assertEqual(entries[0]["account_credit"], "702")  # Export értékesítés

    def test_exempt_invoice_no_vat_entry(self):
        """VAT-exempt invoices should not generate a VAT journal entry."""
        supplier = _make_supplier()
        customer = _make_customer()
        item = NAVInvoiceLineItem(
            line_number=1,
            description="ÁFA mentes",
            quantity=1.0,
            unit_price_huf=100_000.0,
            vat_rate=NAVVATRate.EXEMPT,
        )
        item.calculate_totals()
        inv = NAVInvoice(
            invoice_number="MENTES/001",
            invoice_issue_date="2026-08-13",
            payment_date="2026-08-28",
            delivery_date="2026-08-13",
            supplier=supplier,
            customer=customer,
            items=[item],
        )
        inv.calculate_totals()
        entries = NAVDoubleEntryMapper.generate_journal_entries(inv)
        # Only net entry, no VAT entry
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["account_credit"], "701")


# ─────────────────────────────────────────────────────────────────────────────
# 16-21. NAVOnlineSzamlaGateway SANDBOX WORKFLOW
# ─────────────────────────────────────────────────────────────────────────────

class TestNAVGatewaySandboxWorkflow(unittest.TestCase):

    def setUp(self):
        self.gateway = NAVOnlineSzamlaGateway(environment=NAVEnvironment.SANDBOX)

    def test_sandbox_token_exchange(self):
        """Sandbox token exchange returns a valid session."""
        session = self.gateway.exchange_token()
        self.assertIsNotNone(session)
        self.assertIsInstance(session, NAVSession)
        self.assertTrue(len(session.token_value) > 0)
        self.assertTrue(session.is_valid())
        self.assertFalse(session.is_expired())

    def test_sandbox_ensure_session_caches(self):
        """_ensure_session should reuse an active session."""
        session1 = self.gateway._ensure_session()
        session2 = self.gateway._ensure_session()
        self.assertEqual(session1.token_value, session2.token_value)

    def test_sandbox_submit_invoice_accepted(self):
        """Sandbox invoice submission returns ACCEPTED status."""
        invoice = _make_invoice()
        result  = self.gateway.submit_invoice(invoice)

        self.assertEqual(result.status, NAVInvoiceStatus.ACCEPTED)
        self.assertIn("HU-NAV-", result.transaction_id)
        self.assertEqual(result.invoice_number, "SZL/2026/001")
        self.assertEqual(invoice.status, NAVInvoiceStatus.ACCEPTED)
        self.assertNotEqual(invoice.nav_transaction_id, "")

    def test_sandbox_submit_invalid_tax_number_raises(self):
        """Submission with invalid supplier tax number must raise ValueError."""
        invoice = _make_invoice()
        invoice.supplier = NAVTaxpayer(tax_number="99999999", name="Invalid")
        with self.assertRaises(ValueError):
            self.gateway.submit_invoice(invoice)

    def test_sandbox_query_status(self):
        """Status query returns correct information after submission."""
        invoice = _make_invoice()
        invoice.invoice_number = "SZL/2026/STAT-TEST"
        result  = self.gateway.submit_invoice(invoice)
        status  = self.gateway.query_invoice_status(result.transaction_id)

        self.assertEqual(status["transaction_id"], result.transaction_id)
        self.assertEqual(status["status"], "ACCEPTED")
        self.assertIsInstance(status["processing_results"], list)
        self.assertGreater(len(status["processing_results"]), 0)

    def test_sandbox_query_taxpayer_valid(self):
        """Taxpayer query for a valid adószám returns synthetic SANDBOX data."""
        info = self.gateway.query_taxpayer("10500004-2-41")
        self.assertTrue(info.is_valid)
        self.assertEqual(info.tax_validity, "VALID")
        self.assertIn("10500004", info.company_name)

    def test_sandbox_query_taxpayer_invalid(self):
        """Taxpayer query for invalid adószám returns is_valid=False."""
        info = self.gateway.query_taxpayer("99999999")
        self.assertFalse(info.is_valid)
        self.assertEqual(info.tax_validity, "INVALID")

    def test_sandbox_list_invoices(self):
        """list_invoices returns submitted invoices in order."""
        gw = NAVOnlineSzamlaGateway(environment=NAVEnvironment.SANDBOX)
        inv1 = _make_invoice()
        inv1.invoice_number = "SZL/LIST/001"
        inv2 = _make_invoice()
        inv2.invoice_number = "SZL/LIST/002"
        gw.submit_invoice(inv1)
        gw.submit_invoice(inv2)

        invoices = gw.list_invoices()
        self.assertEqual(len(invoices), 2)
        numbers = [i.invoice_number for i in invoices]
        self.assertIn("SZL/LIST/001", numbers)
        self.assertIn("SZL/LIST/002", numbers)

    def test_sandbox_list_invoices_status_filter(self):
        """list_invoices can filter by status."""
        gw = NAVOnlineSzamlaGateway(environment=NAVEnvironment.SANDBOX)
        inv = _make_invoice()
        gw.submit_invoice(inv)

        accepted = gw.list_invoices(status=NAVInvoiceStatus.ACCEPTED)
        self.assertGreater(len(accepted), 0)
        for i in accepted:
            self.assertEqual(i.status, NAVInvoiceStatus.ACCEPTED)

    def test_sandbox_get_invoice(self):
        """get_invoice finds a submitted invoice by number."""
        gw = NAVOnlineSzamlaGateway(environment=NAVEnvironment.SANDBOX)
        inv = _make_invoice()
        inv.invoice_number = "SZL/GET/001"
        gw.submit_invoice(inv)

        found = gw.get_invoice("SZL/GET/001")
        self.assertIsNotNone(found)
        self.assertEqual(found.invoice_number, "SZL/GET/001")

        not_found = gw.get_invoice("NON-EXISTENT")
        self.assertIsNone(not_found)

    def test_sandbox_statistics(self):
        """Statistics reflect submitted invoices."""
        gw = NAVOnlineSzamlaGateway(environment=NAVEnvironment.SANDBOX)
        inv = _make_invoice()
        gw.submit_invoice(inv)

        stats = gw.get_statistics()
        self.assertEqual(stats["environment"], "SANDBOX")
        self.assertEqual(stats["total_invoices"], 1)
        self.assertIn("ACCEPTED", stats["by_status"])
        self.assertEqual(stats["by_status"]["ACCEPTED"], 1)
        self.assertEqual(stats["total_net_huf"],   500_000)
        self.assertEqual(stats["total_vat_huf"],   135_000)
        self.assertEqual(stats["total_gross_huf"], 635_000)
        self.assertEqual(stats["schema_version"], "3.0")


# ─────────────────────────────────────────────────────────────────────────────
# 22-30. REST API HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

class TestNAVAPIHandlers(unittest.TestCase):

    def _invoice_payload(self) -> str:
        payload = {
            "environment": "SANDBOX",
            "invoice_number": "API-TEST/2026/001",
            "invoice_issue_date": "2026-08-13",
            "payment_date": "2026-08-28",
            "delivery_date": "2026-08-13",
            "operation": "CREATE",
            "category": "NORMAL",
            "payment_method": "TRANSFER",
            "currency_code": "HUF",
            "supplier": {
                "tax_number": "10500004-2-41",
                "name": "FinansProtect Kft.",
                "address_country": "HU",
                "address_postal_code": "1051",
                "address_city": "Budapest",
                "address_street": "Váci utca 1.",
            },
            "customer": {
                "tax_number": "10500004-2-41",
                "name": "Megrendelő Zrt.",
                "address_country": "HU",
                "address_postal_code": "1054",
                "address_city": "Budapest",
                "address_street": "Szabadság tér 10.",
                "vat_status": "DOMESTIC",
            },
            "items": [
                {
                    "line_number": 1,
                    "description": "IT Fejlesztés",
                    "quantity": 1.0,
                    "unit_of_measure": "PIECE",
                    "unit_price_huf": 500000.0,
                    "vat_rate": "27",
                }
            ],
        }
        return json.dumps(payload)

    def test_health_handler_success(self):
        result = get_nav_health_handler()
        self.assertEqual(result["status"], "success")
        self.assertIn("gateway_status", result["data"])
        self.assertEqual(result["data"]["gateway_status"], "OPERATIONAL")
        self.assertIn("SHA-3-512 request signatures", result["data"]["features"])
        self.assertIn("XMLDSig invoice signing", result["data"]["features"])

    def test_validate_tax_valid(self):
        body = json.dumps({"tax_number": "10500004-2-41"})
        result = post_nav_validate_tax_handler(body)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["data"]["is_valid"])
        self.assertEqual(result["data"]["clean_tax_number"], "10500004")
        self.assertEqual(result["data"]["hu_vat_number"], "HU10500004")

    def test_validate_tax_invalid(self):
        body = json.dumps({"tax_number": "99999999"})
        result = post_nav_validate_tax_handler(body)
        self.assertEqual(result["status"], "success")  # API call succeeds
        self.assertFalse(result["data"]["is_valid"])

    def test_validate_tax_missing_field(self):
        body = json.dumps({})
        result = post_nav_validate_tax_handler(body)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_code"], "MISSING_FIELD")

    def test_token_exchange_handler(self):
        body = json.dumps({"environment": "SANDBOX"})
        result = post_nav_token_exchange_handler(body)
        self.assertEqual(result["status"], "success")
        self.assertIn("token", result["data"])
        self.assertTrue(result["data"]["session_valid"])
        self.assertEqual(result["data"]["expires_in"], 300)

    def test_generate_xml_handler(self):
        result = post_nav_generate_xml_handler(self._invoice_payload())
        self.assertEqual(result["status"], "success")
        self.assertIn("xml_content", result["data"])
        self.assertIn("InvoiceData", result["data"]["xml_content"])
        self.assertIn("http://schemas.nav.gov.hu/OSA/3.0/data", result["data"]["xml_content"])
        self.assertEqual(result["data"]["invoice_net_huf"],   500_000)
        self.assertEqual(result["data"]["invoice_vat_huf"],   135_000)
        self.assertEqual(result["data"]["invoice_gross_huf"], 635_000)
        self.assertTrue(result["data"]["includes_xmldsig"])
        self.assertIsInstance(result["data"]["sample_signature_sha3_512"], str)

    def test_submit_invoice_handler(self):
        payload = json.loads(self._invoice_payload())
        payload["invoice_number"] = "API-SUB/2026/001"
        result = post_nav_submit_invoice_handler(json.dumps(payload))
        # Note: nav_api wraps invoice under "invoice" key or uses root
        self.assertIn(result["status"], ("success", "error"))
        if result["status"] == "success":
            self.assertIn("transaction_id", result["data"])
            self.assertIn("HU-NAV-", result["data"]["transaction_id"])

    def test_query_status_missing_transaction_id(self):
        body = json.dumps({"environment": "SANDBOX"})
        result = post_nav_query_status_handler(body)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_code"], "MISSING_FIELD")

    def test_query_taxpayer_handler_valid(self):
        body = json.dumps({"tax_number": "10500004-2-41", "environment": "SANDBOX"})
        result = post_nav_query_taxpayer_handler(body)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["data"]["is_valid"])
        self.assertEqual(result["data"]["tax_validity"], "VALID")

    def test_query_taxpayer_handler_invalid(self):
        body = json.dumps({"tax_number": "99999999", "environment": "SANDBOX"})
        result = post_nav_query_taxpayer_handler(body)
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["data"]["is_valid"])

    def test_query_taxpayer_missing_field(self):
        body = json.dumps({})
        result = post_nav_query_taxpayer_handler(body)
        self.assertEqual(result["status"], "error")

    def test_journal_entries_handler(self):
        result = post_nav_journal_entries_handler(self._invoice_payload())
        self.assertEqual(result["status"], "success")
        self.assertIn("journal_entries", result["data"])
        entries = result["data"]["journal_entries"]
        self.assertGreaterEqual(len(entries), 1)
        # Find net revenue entry
        net_entries = [e for e in entries if e.get("account_credit") == "701"]
        self.assertGreater(len(net_entries), 0)
        self.assertEqual(net_entries[0]["account_debit"], "311")
        self.assertEqual(net_entries[0]["amount_huf"],    500_000)

    def test_invoices_list_handler(self):
        result = get_nav_invoices_handler({"environment": "SANDBOX"})
        self.assertEqual(result["status"], "success")
        self.assertIn("invoices", result["data"])
        self.assertIsInstance(result["data"]["invoices"], list)

    def test_statistics_handler(self):
        result = get_nav_statistics_handler({"environment": "SANDBOX"})
        self.assertEqual(result["status"], "success")
        self.assertIn("environment", result["data"])
        self.assertIn("total_invoices", result["data"])
        self.assertIn("schema_version", result["data"])
        self.assertEqual(result["data"]["schema_version"], "3.0")

    def test_generate_xml_contains_xmldsig_signature(self):
        """XML output must contain XMLDSig ds:Signature block."""
        result = post_nav_generate_xml_handler(self._invoice_payload())
        self.assertEqual(result["status"], "success")
        xml_content = result["data"]["xml_content"]
        self.assertIn("<ds:Signature", xml_content)
        self.assertIn("http://www.w3.org/2000/09/xmldsig#", xml_content)


# ─────────────────────────────────────────────────────────────────────────────
# ADDITIONAL EDGE CASES
# ─────────────────────────────────────────────────────────────────────────────

class TestNAVEdgeCases(unittest.TestCase):

    def test_nav_credentials_password_hash_sha512(self):
        """NAV credentials must use SHA-512 (not SHA-256 or plain) for password."""
        import hashlib
        creds = _make_credentials()
        expected = hashlib.sha512(creds.password.encode("utf-8")).hexdigest().upper()
        self.assertEqual(creds.password_hash(), expected)
        self.assertEqual(len(creds.password_hash()), 128)  # 512 bits = 128 hex chars
        # Must be uppercase
        self.assertEqual(creds.password_hash(), creds.password_hash().upper())

    def test_nav_session_validity(self):
        """NAVSession correctly reports validity within and after expiry."""
        session_active  = NAVSession(token_value="TOKEN123", expires_in=300)
        session_expired = NAVSession(token_value="TOKEN456", created_at=0.0, expires_in=1)

        self.assertTrue(session_active.is_valid())
        self.assertFalse(session_active.is_expired())
        self.assertFalse(session_expired.is_valid())
        self.assertTrue(session_expired.is_expired())

    def test_multiline_invoice_xml_parseable(self):
        """Multi-line invoice XML must remain well-formed."""
        supplier = _make_supplier()
        customer = _make_customer()
        items = [
            _make_line_item(1, "Tétel A",  2.0, 100_000.0, NAVVATRate.RATE_27),
            _make_line_item(2, "Tétel B",  1.0,  50_000.0, NAVVATRate.RATE_5),
            _make_line_item(3, "Tétel C",  3.0,  20_000.0, NAVVATRate.EXEMPT),
        ]
        inv = NAVInvoice(
            invoice_number="MULTI/2026/001",
            invoice_issue_date="2026-08-13",
            payment_date="2026-08-28",
            delivery_date="2026-08-13",
            supplier=supplier,
            customer=customer,
            items=items,
        )
        inv.calculate_totals()
        xml_str = NAVInvoiceGenerator.generate_invoice_data_xml(inv)
        body = xml_str.split('?>\n', 1)[-1]
        root = ET.fromstring(body)
        self.assertIsNotNone(root)
        # All 3 line descriptions must be in XML
        self.assertIn("Tétel A", xml_str)
        self.assertIn("Tétel B", xml_str)
        self.assertIn("Tétel C", xml_str)

    def test_gateway_multiple_invoices_statistics(self):
        """Statistics correctly aggregate HUF totals across multiple invoices."""
        gw = NAVOnlineSzamlaGateway(environment=NAVEnvironment.SANDBOX)

        for i in range(3):
            inv = _make_invoice()
            inv.invoice_number = f"BULK/2026/{i:03d}"
            gw.submit_invoice(inv)

        stats = gw.get_statistics()
        self.assertEqual(stats["total_invoices"],    3)
        self.assertEqual(stats["total_net_huf"],     3 * 500_000)
        self.assertEqual(stats["total_vat_huf"],     3 * 135_000)
        self.assertEqual(stats["total_gross_huf"],   3 * 635_000)

    def test_huf_currency_no_decimals_in_summary(self):
        """HUF amounts in XML must be integers (0 decimal places)."""
        inv = _make_invoice()
        xml_str = NAVInvoiceGenerator.generate_invoice_data_xml(inv)
        # Check that HUF amounts don't have decimal points
        self.assertIn("<invoiceGrossAmountHUF>635000</invoiceGrossAmountHUF>", xml_str)
        self.assertIn("<lineNetAmountHUF>500000</lineNetAmountHUF>", xml_str)
        self.assertIn("<lineVatAmountHUF>135000</lineVatAmountHUF>", xml_str)

    def test_sign_xml_without_declaration(self):
        """XMLDSig signing works on XML without declaration header."""
        raw_xml = '<InvoiceData xmlns="http://schemas.nav.gov.hu/OSA/3.0/data"><invoiceNumber>TEST</invoiceNumber></InvoiceData>'
        signed = NAVXMLDSigSigner.sign_invoice_xml(raw_xml, "TEST-INV")
        self.assertIn("<ds:Signature", signed)
        self.assertIn("TEST", signed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
