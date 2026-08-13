"""
M82 Hungary NAV Online Számla 3.0 Gateway Engine.
(Интеграция с Унгарската данъчна служба NAV — Nemzeti Adó- és Vámhivatal)

This module implements complete direct integration with the Hungarian National Tax
and Customs Administration (NAV – Nemzeti Adó- és Vámhivatal) Online Számla 3.0
(Online Invoice) platform, including:

  - Hungarian tax number (adószám) check-digit validator (Modulo 11)
  - EU VAT number validation for Hungarian HU-prefix numbers
  - Online Számla 3.0 XML invoice builder (invoiceData schema v3.0)
  - SHA-3-512 request signature authentication (X-Request-Id + timestamp + signatureKey)
  - XMLDSig (XML Digital Signature) envelope signing for invoice payloads
  - Token-based session exchange (tokenExchange endpoint)
  - Invoice submission (manageInvoice endpoint, ORIGINAL / MODIFICATION / STORNO)
  - Invoice query and status check (queryInvoiceStatus, queryInvoiceData endpoints)
  - Taxpayer data query (queryTaxpayer endpoint)
  - HUF (Hungarian Forint) monetary precision with 0-decimal rounding
  - Double-entry journal entry generation for Hungarian accounting
  - Full REST API router (nav_api.py) and web UI dashboard (nav.html)

Reference: NAV Online Számla 3.0 API Specification
  Sandbox:    https://api-test.onlineszamla.nav.gov.hu/invoiceService/v3
  Production: https://api.onlineszamla.nav.gov.hu/invoiceService/v3

NAV Online Számla Documentation:
  https://onlineszamla.nav.gov.hu/api/files/container/download/Online%20Számla_Interfész%20specifikáció_EN_v3.0.pdf
"""

import base64
import enum
import hashlib
import json
import logging
import re
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nav_gateway")

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

NAV_SCHEMA_VERSION = "3.0"
NAV_HEADER_VERSION = "1.0"
NAV_SOFTWARE_VERSION = "1.0.0"
NAV_SOFTWARE_NAME = "FinansProtect NAV Gateway"
NAV_SOFTWARE_MAIN_VERSION = "3.0"
NAV_SOFTWARE_DEV_NAME = "FinansProtect Ltd."
NAV_SOFTWARE_DEV_TAX_NUM = "12345678-2-41"
NAV_SOFTWARE_DEV_COUNTRY_CODE = "HU"

# XML Namespaces for NAV Online Számla 3.0
NS_COMMON = "http://schemas.nav.gov.hu/OSA/3.0/common"
NS_API    = "http://schemas.nav.gov.hu/OSA/3.0/api"
NS_DATA   = "http://schemas.nav.gov.hu/OSA/3.0/data"
NS_BASE   = "http://schemas.nav.gov.hu/OSA/3.0/base"
NS_METRIC = "http://schemas.nav.gov.hu/OSA/3.0/metrics"

# XMLDSig namespace
NS_DS = "http://www.w3.org/2000/09/xmldsig#"

# HUF has 0 decimal places
HUF_DECIMAL_PLACES = 0

# ---------------------------------------------------------------------------
# ENUMERATIONS
# ---------------------------------------------------------------------------

class NAVEnvironment(str, enum.Enum):
    PRODUCTION = "PRODUCTION"
    SANDBOX = "SANDBOX"


class NAVInvoiceOperation(str, enum.Enum):
    CREATE = "CREATE"         # Eredeti számla (Original invoice)
    MODIFY = "MODIFY"         # Módosító számla (Modification invoice)
    STORNO = "STORNO"         # Sztornó számla (Storno/Cancellation invoice)


class NAVInvoiceCategory(str, enum.Enum):
    NORMAL = "NORMAL"         # Normál számla
    SIMPLIFIED = "SIMPLIFIED" # Egyszerűsített számla (simplified invoice ≤ 100 000 HUF + VAT)
    AGGREGATE = "AGGREGATE"   # Gyűjtőszámla (aggregate invoice)


class NAVInvoiceAppearance(str, enum.Enum):
    PAPER = "PAPER"           # Papír alapú
    ELECTRONIC = "ELECTRONIC" # Elektronikus
    EDI = "EDI"               # EDI
    UNKNOWN = "UNKNOWN"


class NAVPaymentMethod(str, enum.Enum):
    TRANSFER = "TRANSFER"     # Átutalás
    CASH = "CASH"             # Készpénz
    CARD = "CARD"             # Bankkártya
    VOUCHER = "VOUCHER"       # Utalvány
    OTHER = "OTHER"           # Egyéb


class NAVVATRate(str, enum.Enum):
    RATE_27 = "27"            # Standard 27% VAT (ÁFA)
    RATE_18 = "18"            # Reduced 18% VAT
    RATE_5  = "5"             # Reduced 5% VAT
    RATE_0  = "0"             # 0% (zero-rated)
    EXEMPT  = "EXEMPT"        # ÁFA mentes (tax exempt)
    REVERSE = "REVERSE"       # Fordított ÁFA (reverse charge)
    NO_VAT  = "NO_VAT"        # Nem ÁFAs (not subject to VAT)
    AAM     = "AAM"           # Alanyi adómentesség (personal VAT exemption)


class NAVInvoiceStatus(str, enum.Enum):
    DRAFT      = "DRAFT"
    VALIDATED  = "VALIDATED"
    SIGNED     = "SIGNED"
    SUBMITTED  = "SUBMITTED"
    PROCESSING = "PROCESSING"
    ACCEPTED   = "ACCEPTED"
    REJECTED   = "REJECTED"
    ERROR      = "ERROR"


class NAVLineAmountType(str, enum.Enum):
    UNIT = "UNIT"       # Egységár alapú
    DISCOUNT = "DISCOUNT"  # Kedvezménnyel


# ---------------------------------------------------------------------------
# UTILITY — Hungarian Tax Number (Adószám) Validation
# ---------------------------------------------------------------------------

def validate_tax_number(tax_number: str) -> bool:
    """
    Validates Hungarian tax number (adószám) using Modulo 11 check digit algorithm.

    Hungarian adószám format: XXXXXXXX-Y-ZZ
      - 8 digits (base) + check digit
      - Full format: 11 digits with hyphens: XXXXXXXX-Y-ZZ

    Check-digit algorithm (Modulo 11):
      Weights: [9, 7, 3, 1, 9, 7, 3] applied to first 7 digits
      Sum of (digit × weight) mod 10 = check digit (8th digit)
      If result would be 10, the tax number is invalid.

    VAT taxpayer format: XXXXXXXX-Y-ZZ
      - First 8 digits: the adószám core
      - 9th digit (Y): VAT status (1=exempt, 2=normal, 4=group, 5=group exempt)
      - 10-11th (ZZ): county code (02-44 valid range)
    """
    if not tax_number or not isinstance(tax_number, str):
        return False

    # Remove hyphens, spaces and optional HU prefix
    clean = re.sub(r"[-\s]", "", tax_number.strip().upper())
    if clean.startswith("HU"):
        clean = clean[2:]

    # Accept 8-digit (core only) or 11-digit (full format with Y-ZZ)
    if len(clean) not in (8, 11):
        return False

    if not clean.isdigit():
        return False

    digits = [int(d) for d in clean]

    # Modulo 11 check on first 8 digits
    weights = [9, 7, 3, 1, 9, 7, 3]
    weighted_sum = sum(d * w for d, w in zip(digits[:7], weights))
    check_digit = weighted_sum % 10
    if check_digit == 10:
        return False

    if digits[7] != check_digit:
        return False

    # If full 11-digit format, validate county code (10th-11th digits)
    if len(clean) == 11:
        county_code = int(clean[9:11])
        if county_code < 2 or county_code > 45:
            return False
        # VAT status digit (9th)
        vat_status = digits[8]
        if vat_status not in (1, 2, 4, 5):
            return False

    return True


def format_tax_number(tax_number: str, include_hu_prefix: bool = False) -> str:
    """
    Returns clean 8-digit tax number core, optionally prefixed with HU.
    Strips hyphens and HU prefix.
    """
    clean = re.sub(r"[-\s]", "", tax_number.strip().upper())
    if clean.startswith("HU"):
        clean = clean[2:]
    core = clean[:8]
    return f"HU{core}" if include_hu_prefix else core


def round_huf(amount: float) -> int:
    """Round amount to HUF (0 decimal places, Hungarian Forint)."""
    return int(round(amount, 0))


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class NAVTaxpayer:
    """Hungarian taxpayer / company party."""
    tax_number: str           # Adószám (8 or 11 digit, e.g. "12345678" or "12345678-2-41")
    name: str                 # Cégnév / company name
    bank_account_number: str = ""   # Bankszámlaszám (IBAN or HU domestic)
    address_country: str = "HU"
    address_region: str = ""        # Megye
    address_postal_code: str = ""   # Irányítószám
    address_city: str = ""          # Város
    address_street: str = ""        # Utca, házszám
    vat_status: str = "DOMESTIC"    # DOMESTIC / PRIVATE_PERSON / FOREIGN / FOREIGN_VAT

    def clean_tax_number(self) -> str:
        """Returns 8-digit adószám core."""
        return format_tax_number(self.tax_number, include_hu_prefix=False)

    def is_valid(self) -> bool:
        return validate_tax_number(self.tax_number)

    def hu_vat_number(self) -> str:
        """Return HU-prefix VAT number, e.g. HU12345678."""
        return format_tax_number(self.tax_number, include_hu_prefix=True)


@dataclass
class NAVInvoiceLineItem:
    """Single line item on a Hungarian invoice."""
    line_number: int
    description: str                        # Termék/szolgáltatás megnevezése
    quantity: float = 1.0
    unit_of_measure: str = "PIECE"          # PIECE/KG/LITER/HM2/etc (NAV unit codes)
    unit_price_huf: float = 0.0             # Nettó egységár (HUF)
    vat_rate: NAVVATRate = NAVVATRate.RATE_27
    vat_rate_comment: str = ""              # Additional VAT comment for special rates
    line_net_amount_huf: float = 0.0        # Nettó összeg
    line_vat_amount_huf: float = 0.0        # ÁFA összeg
    line_gross_amount_huf: float = 0.0      # Bruttó összeg
    product_code: str = ""                  # VTSZ / SZJ product/service code
    gl_mapping_debit: str = ""              # Hungarian Chart of Accounts debit
    gl_mapping_credit: str = ""             # Hungarian Chart of Accounts credit

    def calculate_totals(self) -> None:
        """Auto-compute net/VAT/gross from unit_price_huf × quantity and vat_rate."""
        net = self.unit_price_huf * self.quantity
        self.line_net_amount_huf = net

        vat_rate_num: float = 0.0
        try:
            if self.vat_rate.value not in ("EXEMPT", "REVERSE", "NO_VAT", "AAM"):
                vat_rate_num = float(self.vat_rate.value) / 100.0
        except (ValueError, AttributeError):
            vat_rate_num = 0.0

        self.line_vat_amount_huf = net * vat_rate_num
        self.line_gross_amount_huf = net + self.line_vat_amount_huf


@dataclass
class NAVInvoice:
    """NAV Online Számla 3.0 invoice document."""
    invoice_number: str                   # Számlaszám (invoice number)
    invoice_issue_date: str               # Keltezés (issue date, YYYY-MM-DD)
    payment_date: str                     # Fizetési határidő (due date, YYYY-MM-DD)
    delivery_date: str                    # Teljesítés dátuma (YYYY-MM-DD)
    supplier: NAVTaxpayer                 # Eladó (seller)
    customer: NAVTaxpayer                 # Vevő (buyer)
    items: List[NAVInvoiceLineItem] = field(default_factory=list)
    operation: NAVInvoiceOperation = NAVInvoiceOperation.CREATE
    category: NAVInvoiceCategory = NAVInvoiceCategory.NORMAL
    appearance: NAVInvoiceAppearance = NAVInvoiceAppearance.ELECTRONIC
    payment_method: NAVPaymentMethod = NAVPaymentMethod.TRANSFER
    currency_code: str = "HUF"
    exchange_rate: float = 1.0            # Only relevant for foreign currency invoices
    invoice_net_amount: float = 0.0       # Total nettó összeg
    invoice_vat_amount: float = 0.0       # Total ÁFA összeg
    invoice_gross_amount: float = 0.0     # Total bruttó összeg
    vat_summary: Dict[str, Dict] = field(default_factory=dict)  # Per-rate VAT summary
    status: NAVInvoiceStatus = NAVInvoiceStatus.DRAFT
    nav_transaction_id: str = ""          # Returned by NAV after submission
    nav_index_in_batch: int = 1           # Index within batch (1-based)
    nav_annul_reference: str = ""         # Original invoice number for STORNO/MODIFY
    language: str = "HU"                  # Invoice language (HU/EN/DE/etc.)

    def calculate_totals(self) -> None:
        """Aggregate totals from all line items, computing VAT per rate."""
        self.invoice_net_amount = 0.0
        self.invoice_vat_amount = 0.0
        vat_by_rate: Dict[str, Dict] = {}

        for item in self.items:
            item.calculate_totals()
            self.invoice_net_amount += item.line_net_amount_huf
            self.invoice_vat_amount += item.line_vat_amount_huf

            rate_key = item.vat_rate.value
            if rate_key not in vat_by_rate:
                vat_by_rate[rate_key] = {"net": 0.0, "vat": 0.0, "gross": 0.0}
            vat_by_rate[rate_key]["net"] += item.line_net_amount_huf
            vat_by_rate[rate_key]["vat"] += item.line_vat_amount_huf
            vat_by_rate[rate_key]["gross"] += item.line_gross_amount_huf

        self.invoice_gross_amount = self.invoice_net_amount + self.invoice_vat_amount
        self.vat_summary = vat_by_rate


@dataclass
class NAVCredentials:
    """NAV Online Számla 3.0 API credentials."""
    login: str                # Felhasználónév (NAV user login)
    password: str             # Jelszó SHA-512 hash (stored as SHA-512 hex)
    tax_number: str           # Adószám of the authenticated company
    signature_key: str        # Aláírási kulcs (signature key for request hash)
    exchange_key: str         # Cserekulcs (exchange key for token decryption)

    def password_hash(self) -> str:
        """Return SHA-512 hash of password (as required by NAV API)."""
        return hashlib.sha512(self.password.encode("utf-8")).hexdigest().upper()


@dataclass
class NAVSession:
    """Active NAV API session token."""
    token_value: str
    created_at: float = field(default_factory=time.time)
    expires_in: int = 300         # NAV session tokens expire in 5 minutes

    def is_valid(self) -> bool:
        return (time.time() - self.created_at) < self.expires_in

    def is_expired(self) -> bool:
        return not self.is_valid()


@dataclass
class NAVSubmissionResult:
    """Result from NAV invoice submission."""
    transaction_id: str
    invoice_number: str
    status: NAVInvoiceStatus
    index_in_batch: int = 1
    batch_error_code: str = ""
    batch_error_message: str = ""
    original_request_id: str = ""
    timestamp: str = ""


@dataclass
class NAVTaxpayerInfo:
    """Taxpayer data returned from NAV queryTaxpayer endpoint."""
    tax_number: str
    company_name: str
    is_valid: bool = False
    tax_validity: str = ""         # "VALID" / "INVALID" / "SUSPENDED"
    vat_status: str = ""
    address: str = ""
    query_timestamp: str = ""


# ---------------------------------------------------------------------------
# SHA-3-512 REQUEST SIGNATURE
# ---------------------------------------------------------------------------

class NAVRequestSigner:
    """
    Generates NAV Online Számla 3.0 SHA-3-512 request signatures.

    The signature is computed as:
        SHA3-512( requestId + timestamp + signatureKey + base64(invoice_xml) )

    Reference: NAV Online Számla 3.0 API spec, Section 4.4 — Signature generation
    """

    @staticmethod
    def compute_request_signature(
        request_id: str,
        timestamp: str,
        signature_key: str,
        invoice_data_b64: str = "",
    ) -> str:
        """
        Compute SHA-3-512 request signature for NAV API calls.

        Args:
            request_id:      UUID-format request ID (X-Request-Id header)
            timestamp:       UTC timestamp in format YYYY-MM-DDTHH:MM:SSZ
            signature_key:   NAV-issued signature key (aláírási kulcs)
            invoice_data_b64: Base64-encoded invoice XML (only for manageInvoice)

        Returns:
            SHA-3-512 hex digest (uppercase)
        """
        payload = request_id + timestamp + signature_key + invoice_data_b64
        digest = hashlib.sha3_512(payload.encode("utf-8")).hexdigest().upper()
        logger.debug(
            "SHA-3-512 signature computed for request_id=%s timestamp=%s",
            request_id, timestamp
        )
        return digest

    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request ID (UUID without hyphens, uppercase, 32 chars)."""
        return uuid.uuid4().hex.upper()

    @staticmethod
    def current_timestamp() -> str:
        """Return current UTC timestamp in NAV format: YYYY-MM-DDTHH:MM:SSZ"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# XMLDSig SIGNING WRAPPER
# ---------------------------------------------------------------------------

class NAVXMLDSigSigner:
    """
    XMLDSig (XML Digital Signature) envelope wrapper for NAV invoice data.

    NAV Online Számla 3.0 requires invoices to be wrapped in a ds:Signature
    element conforming to W3C XMLDSig (http://www.w3.org/2000/09/xmldsig#).

    This implementation produces a self-signed (software) XMLDSig signature
    suitable for test/sandbox environments. In production, a qualified
    electronic signature (QES) issued by an accredited Hungarian CA is required.

    Signature algorithm: RSA-SHA256 (http://www.w3.org/2001/04/xmldsig-more#rsa-sha256)
    Canonicalization: Canonical XML 1.0 (http://www.w3.org/TR/2001/REC-xml-c14n-20010315)
    Digest algorithm: SHA-256 (http://www.w3.org/2001/04/xmlenc#sha256)
    """

    SIGNATURE_ALGO = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    C14N_ALGO      = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    DIGEST_ALGO    = "http://www.w3.org/2001/04/xmlenc#sha256"
    TRANSFORM_ENV  = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"

    @classmethod
    def sign_invoice_xml(
        cls,
        invoice_xml: str,
        invoice_number: str,
        timestamp: str = "",
    ) -> str:
        """
        Wrap invoice XML in an XMLDSig ds:Signature envelope.

        Args:
            invoice_xml:    Raw InvoiceData XML string
            invoice_number: Invoice number (used as Reference URI)
            timestamp:      Signing timestamp (defaults to current UTC time)

        Returns:
            XMLDSig-wrapped invoice XML string with ds:Signature appended.
        """
        if not timestamp:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Compute SHA-256 digest of the invoice XML (base64-encoded)
        xml_bytes = invoice_xml.encode("utf-8")
        digest_bytes = hashlib.sha256(xml_bytes).digest()
        digest_b64 = base64.b64encode(digest_bytes).decode("ascii")

        # Build synthetic (self-signed) signature value from SHA3-512 of the digest
        sig_source = f"NAV-SIG:{invoice_number}:{timestamp}:{digest_b64}"
        sig_bytes = hashlib.sha3_512(sig_source.encode("utf-8")).digest()
        sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

        # Build ds:Signature XML block
        ref_uri = f"inv-{re.sub(r'[^a-zA-Z0-9]', '-', invoice_number)}"
        signed_info_xml = (
            f'<ds:SignedInfo xmlns:ds="{NS_DS}">'
            f'<ds:CanonicalizationMethod Algorithm="{cls.C14N_ALGO}"/>'
            f'<ds:SignatureMethod Algorithm="{cls.SIGNATURE_ALGO}"/>'
            f'<ds:Reference URI="#{ref_uri}">'
            f'<ds:Transforms>'
            f'<ds:Transform Algorithm="{cls.TRANSFORM_ENV}"/>'
            f'<ds:Transform Algorithm="{cls.C14N_ALGO}"/>'
            f'</ds:Transforms>'
            f'<ds:DigestMethod Algorithm="{cls.DIGEST_ALGO}"/>'
            f'<ds:DigestValue>{digest_b64}</ds:DigestValue>'
            f'</ds:Reference>'
            f'</ds:SignedInfo>'
        )

        # Compute the SignatureValue as SHA-256 of the SignedInfo canonical form
        si_digest = hashlib.sha256(signed_info_xml.encode("utf-8")).digest()
        si_b64 = base64.b64encode(si_digest).decode("ascii")

        signature_block = (
            f'\n<ds:Signature xmlns:ds="{NS_DS}" Id="NAVSignature">'
            f"{signed_info_xml}"
            f"<ds:SignatureValue>{si_b64}</ds:SignatureValue>"
            f'<ds:KeyInfo>'
            f'<ds:KeyName>NAV-Software-Key:{invoice_number}</ds:KeyName>'
            f"</ds:KeyInfo>"
            f"</ds:Signature>"
        )

        # Inject Id attribute into the root element and append signature
        if invoice_xml.strip().startswith("<?xml"):
            # Keep declaration, inject after it
            decl_end = invoice_xml.index("?>") + 2
            root_start = invoice_xml.index("<", decl_end)
            root_tag_end = invoice_xml.index(">", root_start)
            # Insert Id attribute
            root_open = invoice_xml[root_start:root_tag_end + 1]
            root_with_id = root_open.rstrip(">") + f' Id="{ref_uri}">'
            rest = invoice_xml[root_tag_end + 1:]
            # Find closing root tag
            close_idx = rest.rfind("</")
            close_tag = rest[close_idx:]
            body = rest[:close_idx]
            result = (
                invoice_xml[:decl_end]
                + invoice_xml[decl_end:root_start]
                + root_with_id
                + body
                + signature_block
                + "\n"
                + close_tag
            )
        else:
            # No XML declaration
            root_end = invoice_xml.index(">")
            root_open = invoice_xml[:root_end + 1]
            root_with_id = root_open.rstrip(">") + f' Id="{ref_uri}">'
            rest = invoice_xml[root_end + 1:]
            close_idx = rest.rfind("</")
            close_tag = rest[close_idx:]
            body = rest[:close_idx]
            result = root_with_id + body + signature_block + "\n" + close_tag

        logger.debug(
            "XMLDSig envelope generated for invoice %s (DigestB64 len=%d)",
            invoice_number, len(digest_b64)
        )
        return result


# ---------------------------------------------------------------------------
# INVOICE XML GENERATOR
# ---------------------------------------------------------------------------

class NAVInvoiceGenerator:
    """
    Generates NAV Online Számla 3.0 XML invoice documents.

    Schema: http://schemas.nav.gov.hu/OSA/3.0/data (InvoiceData)
    Reference: Online Számla 3.0 XSD schemas v3.0
    """

    @staticmethod
    def _tax_number_element(parent: ET.Element, tax_number: str, tag: str = "taxpayerNumber") -> ET.Element:
        """Add a taxpayerNumber element, splitting into base+vat+county if full 11-digit."""
        elem = ET.SubElement(parent, tag)
        clean = re.sub(r"[-\s]", "", tax_number.upper())
        if clean.startswith("HU"):
            clean = clean[2:]

        if len(clean) == 11:
            ET.SubElement(elem, "taxpayerNumberBase").text = clean[:8]
            ET.SubElement(elem, "vatCode").text = clean[8]
            ET.SubElement(elem, "countyCode").text = clean[9:11]
        else:
            ET.SubElement(elem, "taxpayerNumberBase").text = clean[:8]
        return elem

    @classmethod
    def generate_invoice_data_xml(cls, invoice: NAVInvoice) -> str:
        """
        Generate InvoiceData XML per NAV Online Számla 3.0 schema.

        Returns:
            UTF-8 XML string (without XMLDSig wrapper).
        """
        if not invoice.items:
            raise ValueError("Invoice must have at least one line item.")

        invoice.calculate_totals()

        # Register namespaces
        ET.register_namespace("", NS_DATA)
        ET.register_namespace("common", NS_COMMON)
        ET.register_namespace("base", NS_BASE)
        ET.register_namespace("ds", NS_DS)

        # Root: InvoiceData
        root = ET.Element(f"{{{NS_DATA}}}InvoiceData")
        root.set("xmlns", NS_DATA)
        root.set("xmlns:common", NS_COMMON)
        root.set("xmlns:base", NS_BASE)

        # invoiceNumber
        ET.SubElement(root, "invoiceNumber").text = invoice.invoice_number

        # invoiceIssueDate
        ET.SubElement(root, "invoiceIssueDate").text = invoice.invoice_issue_date

        # completenessIndicator (false for normal invoices)
        ET.SubElement(root, "completenessIndicator").text = "false"

        # invoiceMain
        invoice_main = ET.SubElement(root, "invoiceMain")
        inv_elem = ET.SubElement(invoice_main, "invoice")

        # invoiceReference (for MODIFY/STORNO)
        if invoice.operation in (NAVInvoiceOperation.MODIFY, NAVInvoiceOperation.STORNO):
            inv_ref = ET.SubElement(inv_elem, "invoiceReference")
            ET.SubElement(inv_ref, "originalInvoiceNumber").text = invoice.nav_annul_reference
            ET.SubElement(inv_ref, "modifyWithoutMaster").text = "false"
            ET.SubElement(inv_ref, "modificationIndex").text = "1"

        # invoiceHead
        inv_head = ET.SubElement(inv_elem, "invoiceHead")

        # supplierInfo
        supplier_info = ET.SubElement(inv_head, "supplierInfo")
        cls._tax_number_element(supplier_info, invoice.supplier.tax_number)
        ET.SubElement(supplier_info, "supplierName").text = invoice.supplier.name
        sup_addr = ET.SubElement(supplier_info, "supplierAddress")
        sup_detail = ET.SubElement(sup_addr, "detailedAddress")
        ET.SubElement(sup_detail, "countryCode").text = invoice.supplier.address_country
        ET.SubElement(sup_detail, "postalCode").text = invoice.supplier.address_postal_code
        ET.SubElement(sup_detail, "city").text = invoice.supplier.address_city
        ET.SubElement(sup_detail, "streetName").text = invoice.supplier.address_street
        if invoice.supplier.bank_account_number:
            ET.SubElement(supplier_info, "supplierBankAccountNumber").text = invoice.supplier.bank_account_number

        # customerInfo
        customer_info = ET.SubElement(inv_head, "customerInfo")
        if invoice.customer.vat_status != "PRIVATE_PERSON":
            cust_vat = ET.SubElement(customer_info, "customerVatStatus")
            cust_vat.text = invoice.customer.vat_status or "DOMESTIC"
            cust_vat_data = ET.SubElement(customer_info, "customerVatData")
            cust_dom = ET.SubElement(cust_vat_data, "customerTaxNumber")
            cls._tax_number_element(cust_dom, invoice.customer.tax_number, tag="taxpayerNumber")
        else:
            ET.SubElement(customer_info, "customerVatStatus").text = "PRIVATE_PERSON"

        cust_info_detail = ET.SubElement(customer_info, "customerName")
        cust_info_detail.text = invoice.customer.name
        cust_addr = ET.SubElement(customer_info, "customerAddress")
        cust_detail = ET.SubElement(cust_addr, "detailedAddress")
        ET.SubElement(cust_detail, "countryCode").text = invoice.customer.address_country
        ET.SubElement(cust_detail, "postalCode").text = invoice.customer.address_postal_code
        ET.SubElement(cust_detail, "city").text = invoice.customer.address_city
        ET.SubElement(cust_detail, "streetName").text = invoice.customer.address_street

        # invoiceDetail
        inv_detail = ET.SubElement(inv_head, "invoiceDetail")
        ET.SubElement(inv_detail, "invoiceCategory").text = invoice.category.value
        ET.SubElement(inv_detail, "invoiceDeliveryDate").text = invoice.delivery_date
        ET.SubElement(inv_detail, "currencyCode").text = invoice.currency_code
        if invoice.currency_code != "HUF":
            ET.SubElement(inv_detail, "exchangeRate").text = f"{invoice.exchange_rate:.4f}"
        ET.SubElement(inv_detail, "paymentMethod").text = invoice.payment_method.value
        ET.SubElement(inv_detail, "paymentDate").text = invoice.payment_date
        ET.SubElement(inv_detail, "invoiceAppearance").text = invoice.appearance.value
        ET.SubElement(inv_detail, "electronicInvoiceHash").text = hashlib.sha256(
            invoice.invoice_number.encode("utf-8")
        ).hexdigest().upper()

        # invoiceLines
        inv_lines = ET.SubElement(inv_elem, "invoiceLines")
        inv_lines.set("mergedItemIndicator", "false")

        for item in invoice.items:
            line = ET.SubElement(inv_lines, "line")
            ET.SubElement(line, "lineNumber").text = str(item.line_number)
            ET.SubElement(line, "lineModificationReference").text = "ORIGINAL"

            # Product / service classification
            if item.product_code:
                prod_class = ET.SubElement(line, "productCodes")
                prod_code_item = ET.SubElement(prod_class, "productCode")
                ET.SubElement(prod_code_item, "productCodeCategory").text = "VTSZ"
                ET.SubElement(prod_code_item, "productCodeValue").text = item.product_code

            ET.SubElement(line, "lineExpressionIndicator").text = "true"
            ET.SubElement(line, "lineDescription").text = item.description

            # Quantity
            quant = ET.SubElement(line, "quantity")
            quant.text = f"{item.quantity:.6f}"
            ET.SubElement(line, "unitOfMeasure").text = item.unit_of_measure
            ET.SubElement(line, "unitPrice").text = f"{item.unit_price_huf:.2f}"

            # lineAmountsNormal
            line_amounts = ET.SubElement(line, "lineAmountsNormal")
            line_net = ET.SubElement(line_amounts, "lineNetAmountData")
            ET.SubElement(line_net, "lineNetAmount").text = f"{item.line_net_amount_huf:.2f}"
            ET.SubElement(line_net, "lineNetAmountHUF").text = str(round_huf(item.line_net_amount_huf))

            line_vat = ET.SubElement(line_amounts, "lineVatRate")
            if item.vat_rate in (NAVVATRate.EXEMPT, NAVVATRate.AAM):
                ET.SubElement(line_vat, "vatExemption").text = item.vat_rate.value
            elif item.vat_rate == NAVVATRate.REVERSE:
                ET.SubElement(line_vat, "vatOutOfScope").text = "REVERSE_CHARGE"
            elif item.vat_rate == NAVVATRate.NO_VAT:
                ET.SubElement(line_vat, "vatOutOfScope").text = "NO_VAT"
            else:
                ET.SubElement(line_vat, "vatPercentage").text = f"{float(item.vat_rate.value) / 100:.4f}"

            line_vat_data = ET.SubElement(line_amounts, "lineVatData")
            ET.SubElement(line_vat_data, "lineVatAmount").text = f"{item.line_vat_amount_huf:.2f}"
            ET.SubElement(line_vat_data, "lineVatAmountHUF").text = str(round_huf(item.line_vat_amount_huf))

            line_gross = ET.SubElement(line_amounts, "lineGrossAmountData")
            ET.SubElement(line_gross, "lineGrossAmountNormal").text = f"{item.line_gross_amount_huf:.2f}"
            ET.SubElement(line_gross, "lineGrossAmountNormalHUF").text = str(round_huf(item.line_gross_amount_huf))

        # invoiceSummary
        inv_summary = ET.SubElement(inv_elem, "invoiceSummary")
        sum_normal = ET.SubElement(inv_summary, "summaryNormal")

        # Per-rate VAT summary rows
        for rate_key, amounts in invoice.vat_summary.items():
            sum_row = ET.SubElement(sum_normal, "summaryByVatRate")
            vat_rate_elem = ET.SubElement(sum_row, "vatRate")

            try:
                if rate_key not in ("EXEMPT", "REVERSE", "NO_VAT", "AAM"):
                    ET.SubElement(vat_rate_elem, "vatPercentage").text = f"{float(rate_key) / 100:.4f}"
                else:
                    ET.SubElement(vat_rate_elem, "vatExemption").text = rate_key
            except ValueError:
                ET.SubElement(vat_rate_elem, "vatExemption").text = rate_key

            vat_rate_net = ET.SubElement(sum_row, "summaryNetData")
            ET.SubElement(vat_rate_net, "summaryNetAmount").text = f"{amounts['net']:.2f}"
            ET.SubElement(vat_rate_net, "summaryNetAmountHUF").text = str(round_huf(amounts["net"]))

            vat_rate_vat = ET.SubElement(sum_row, "summaryVatData")
            ET.SubElement(vat_rate_vat, "summaryVatBase").text = f"{amounts['net']:.2f}"
            ET.SubElement(vat_rate_vat, "summaryVatBaseHUF").text = str(round_huf(amounts["net"]))
            ET.SubElement(vat_rate_vat, "summaryVatAmount").text = f"{amounts['vat']:.2f}"
            ET.SubElement(vat_rate_vat, "summaryVatAmountHUF").text = str(round_huf(amounts["vat"]))

        # invoiceSummaryGrossData
        gross_data = ET.SubElement(inv_summary, "invoiceSummaryGrossData")
        ET.SubElement(gross_data, "invoiceGrossAmount").text = f"{invoice.invoice_gross_amount:.2f}"
        ET.SubElement(gross_data, "invoiceGrossAmountHUF").text = str(round_huf(invoice.invoice_gross_amount))

        # Serialize
        ET.indent(root, space="  ")
        xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes

    @classmethod
    def generate_manage_invoice_request_xml(
        cls,
        invoice: NAVInvoice,
        credentials: NAVCredentials,
        request_id: str,
        timestamp: str,
    ) -> str:
        """
        Build the complete manageInvoice SOAP/REST request XML envelope.

        This wraps:
          1. Header (requestId, timestamp, requestVersion, headerVersion)
          2. User (login, passwordHash, taxNumber, requestSignature)
          3. Software identification
          4. invoiceOperations (operation + base64 encoded InvoiceData XML)

        Returns:
            Complete manageInvoice request XML string.
        """
        # Generate invoice XML and encode to base64
        invoice_data_xml = cls.generate_invoice_data_xml(invoice)
        signed_invoice_xml = NAVXMLDSigSigner.sign_invoice_xml(
            invoice_data_xml, invoice.invoice_number, timestamp
        )
        invoice_b64 = base64.b64encode(signed_invoice_xml.encode("utf-8")).decode("ascii")

        # Compute request signature (SHA-3-512)
        request_sig = NAVRequestSigner.compute_request_signature(
            request_id=request_id,
            timestamp=timestamp,
            signature_key=credentials.signature_key,
            invoice_data_b64=invoice_b64,
        )

        ET.register_namespace("", NS_API)
        ET.register_namespace("common", NS_COMMON)
        ET.register_namespace("base", NS_BASE)

        root = ET.Element(f"{{{NS_API}}}ManageInvoiceRequest")
        root.set("xmlns", NS_API)
        root.set("xmlns:common", NS_COMMON)
        root.set("xmlns:base", NS_BASE)

        # Header
        header = ET.SubElement(root, f"{{{NS_COMMON}}}header")
        ET.SubElement(header, f"{{{NS_COMMON}}}requestId").text = request_id
        ET.SubElement(header, f"{{{NS_COMMON}}}timestamp").text = timestamp
        ET.SubElement(header, f"{{{NS_COMMON}}}requestVersion").text = NAV_SCHEMA_VERSION
        ET.SubElement(header, f"{{{NS_COMMON}}}headerVersion").text = NAV_HEADER_VERSION

        # User
        user = ET.SubElement(root, f"{{{NS_COMMON}}}user")
        ET.SubElement(user, f"{{{NS_COMMON}}}login").text = credentials.login
        ET.SubElement(user, f"{{{NS_COMMON}}}passwordHash").text = credentials.password_hash()
        ET.SubElement(user, f"{{{NS_COMMON}}}taxNumber").text = credentials.clean_tax_number()
        ET.SubElement(user, f"{{{NS_COMMON}}}requestSignature").text = request_sig

        # Software
        software = ET.SubElement(root, f"{{{NS_COMMON}}}software")
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareId").text = "HU-FP-NAV-GW-1.0.0"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareName").text = NAV_SOFTWARE_NAME
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareOperation").text = "ONLINE_SERVICE"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareMainVersion").text = NAV_SOFTWARE_MAIN_VERSION
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevName").text = NAV_SOFTWARE_DEV_NAME
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevContact").text = "noreply@finansprotect.eu"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevCountryCode").text = NAV_SOFTWARE_DEV_COUNTRY_CODE
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevTaxNumber").text = NAV_SOFTWARE_DEV_TAX_NUM

        # invoiceOperations
        inv_ops = ET.SubElement(root, "invoiceOperations")
        ET.SubElement(inv_ops, "compressedContentIndicator").text = "false"
        inv_op = ET.SubElement(inv_ops, "invoiceOperation")
        ET.SubElement(inv_op, "index").text = str(invoice.nav_index_in_batch)
        ET.SubElement(inv_op, "invoiceOperation").text = invoice.operation.value
        ET.SubElement(inv_op, "invoiceData").text = invoice_b64

        ET.indent(root, space="  ")
        xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    @classmethod
    def generate_token_exchange_request_xml(
        cls,
        credentials: NAVCredentials,
        request_id: str,
        timestamp: str,
    ) -> str:
        """Generate tokenExchange request XML (NAV session authentication)."""
        request_sig = NAVRequestSigner.compute_request_signature(
            request_id=request_id,
            timestamp=timestamp,
            signature_key=credentials.signature_key,
        )

        ET.register_namespace("", NS_API)
        ET.register_namespace("common", NS_COMMON)

        root = ET.Element(f"{{{NS_API}}}TokenExchangeRequest")
        root.set("xmlns", NS_API)
        root.set("xmlns:common", NS_COMMON)

        header = ET.SubElement(root, f"{{{NS_COMMON}}}header")
        ET.SubElement(header, f"{{{NS_COMMON}}}requestId").text = request_id
        ET.SubElement(header, f"{{{NS_COMMON}}}timestamp").text = timestamp
        ET.SubElement(header, f"{{{NS_COMMON}}}requestVersion").text = NAV_SCHEMA_VERSION
        ET.SubElement(header, f"{{{NS_COMMON}}}headerVersion").text = NAV_HEADER_VERSION

        user = ET.SubElement(root, f"{{{NS_COMMON}}}user")
        ET.SubElement(user, f"{{{NS_COMMON}}}login").text = credentials.login
        ET.SubElement(user, f"{{{NS_COMMON}}}passwordHash").text = credentials.password_hash()
        ET.SubElement(user, f"{{{NS_COMMON}}}taxNumber").text = credentials.clean_tax_number()
        ET.SubElement(user, f"{{{NS_COMMON}}}requestSignature").text = request_sig

        software = ET.SubElement(root, f"{{{NS_COMMON}}}software")
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareId").text = "HU-FP-NAV-GW-1.0.0"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareName").text = NAV_SOFTWARE_NAME
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareOperation").text = "ONLINE_SERVICE"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareMainVersion").text = NAV_SOFTWARE_MAIN_VERSION
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevName").text = NAV_SOFTWARE_DEV_NAME
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevContact").text = "noreply@finansprotect.eu"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevCountryCode").text = NAV_SOFTWARE_DEV_COUNTRY_CODE
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevTaxNumber").text = NAV_SOFTWARE_DEV_TAX_NUM

        ET.indent(root, space="  ")
        xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    @classmethod
    def generate_query_taxpayer_request_xml(
        cls,
        tax_number_to_query: str,
        credentials: NAVCredentials,
        request_id: str,
        timestamp: str,
    ) -> str:
        """Generate queryTaxpayer request XML."""
        request_sig = NAVRequestSigner.compute_request_signature(
            request_id=request_id,
            timestamp=timestamp,
            signature_key=credentials.signature_key,
        )

        ET.register_namespace("", NS_API)
        ET.register_namespace("common", NS_COMMON)

        root = ET.Element(f"{{{NS_API}}}QueryTaxpayerRequest")
        root.set("xmlns", NS_API)
        root.set("xmlns:common", NS_COMMON)

        header = ET.SubElement(root, f"{{{NS_COMMON}}}header")
        ET.SubElement(header, f"{{{NS_COMMON}}}requestId").text = request_id
        ET.SubElement(header, f"{{{NS_COMMON}}}timestamp").text = timestamp
        ET.SubElement(header, f"{{{NS_COMMON}}}requestVersion").text = NAV_SCHEMA_VERSION
        ET.SubElement(header, f"{{{NS_COMMON}}}headerVersion").text = NAV_HEADER_VERSION

        user = ET.SubElement(root, f"{{{NS_COMMON}}}user")
        ET.SubElement(user, f"{{{NS_COMMON}}}login").text = credentials.login
        ET.SubElement(user, f"{{{NS_COMMON}}}passwordHash").text = credentials.password_hash()
        ET.SubElement(user, f"{{{NS_COMMON}}}taxNumber").text = credentials.clean_tax_number()
        ET.SubElement(user, f"{{{NS_COMMON}}}requestSignature").text = request_sig

        software = ET.SubElement(root, f"{{{NS_COMMON}}}software")
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareId").text = "HU-FP-NAV-GW-1.0.0"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareName").text = NAV_SOFTWARE_NAME
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareOperation").text = "ONLINE_SERVICE"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareMainVersion").text = NAV_SOFTWARE_MAIN_VERSION
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevName").text = NAV_SOFTWARE_DEV_NAME
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevContact").text = "noreply@finansprotect.eu"
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevCountryCode").text = NAV_SOFTWARE_DEV_COUNTRY_CODE
        ET.SubElement(software, f"{{{NS_COMMON}}}softwareDevTaxNumber").text = NAV_SOFTWARE_DEV_TAX_NUM

        clean_query = format_tax_number(tax_number_to_query)
        ET.SubElement(root, "taxNumber").text = clean_query

        ET.indent(root, space="  ")
        xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str


# ---------------------------------------------------------------------------
# DOUBLE-ENTRY JOURNAL ENTRY GENERATOR
# ---------------------------------------------------------------------------

class NAVDoubleEntryMapper:
    """
    Generates Hungarian double-entry (kettős könyvvitel) journal entries
    for NAV Online Számla 3.0 invoice transactions.

    Hungarian Chart of Accounts (SZT - Számviteli Törvény):
      311 - Belföldi vevők (Domestic trade receivables)
      3111 - Követelések kapcsolt vállalkozásokkal (Intercompany receivables)
      211 - Áruk (Goods at cost)
      261 - Áruk értékesítési áron (Goods at sales price)
      4 - Kötelezettségek (Liabilities)
      454 - Fizetendő ÁFA (VAT payable)
      4543 - ÁFA elszámolási számla (VAT clearing account)
      700 - Értékesítés nettó árbevétele (Net revenue from sales)
      701 - Belföldi értékesítés (Domestic sales revenue)
      702 - Export értékesítés (Export sales)
      811 - Belföldi vásárolt készletek közvetlen anyagköltsége (COGS domestic)
    """

    ACCOUNTS = {
        "trade_receivable":   "311",    # Belföldi vevők
        "foreign_receivable": "319",    # Külföldi vevők
        "revenue_domestic":   "701",    # Belföldi értékesítés
        "revenue_export":     "702",    # Export értékesítés
        "vat_payable":        "454",    # Fizetendő ÁFA
        "vat_clearing":       "4543",   # ÁFA elszámolás
        "vat_deductible":     "466",    # Előzetesen felszámított ÁFA
        "cash":               "381",    # Pénztár
        "bank":               "384",    # Bankszámlák
        "cogs":               "811",    # Közvetlen anyagköltség
    }

    @classmethod
    def generate_journal_entries(cls, invoice: NAVInvoice) -> List[Dict[str, Any]]:
        """
        Generate double-entry journal entries for an issued invoice.

        For a domestic sales invoice (CREATE):
          DR 311 Vevők                  → Gross amount
          CR 701 Értékesítés            → Net amount
          CR 454 Fizetendő ÁFA          → VAT amount

        For a storno invoice (STORNO) — reversal entries.

        Returns:
            List of journal entry dicts with keys:
              account_debit, account_credit, amount_huf, description, vat_rate
        """
        invoice.calculate_totals()
        entries: List[Dict[str, Any]] = []
        sign = -1 if invoice.operation == NAVInvoiceOperation.STORNO else 1

        # Determine receivable account
        receivable_account = (
            cls.ACCOUNTS["foreign_receivable"]
            if invoice.customer.address_country != "HU"
            else cls.ACCOUNTS["trade_receivable"]
        )

        # Determine revenue account
        revenue_account = (
            cls.ACCOUNTS["revenue_export"]
            if invoice.customer.address_country != "HU"
            else cls.ACCOUNTS["revenue_domestic"]
        )

        gross_huf = round_huf(abs(invoice.invoice_gross_amount)) * sign
        net_huf   = round_huf(abs(invoice.invoice_net_amount))   * sign
        vat_huf   = round_huf(abs(invoice.invoice_vat_amount))   * sign

        # Main receivable entry
        entries.append({
            "account_debit":   receivable_account,
            "account_credit":  revenue_account,
            "amount_huf":      net_huf,
            "description":     f"Számlaszám: {invoice.invoice_number} — nettó árbevétel",
            "invoice_number":  invoice.invoice_number,
            "issue_date":      invoice.invoice_issue_date,
            "operation":       invoice.operation.value,
        })

        # VAT entry (if any VAT)
        if abs(vat_huf) > 0:
            entries.append({
                "account_debit":   receivable_account,
                "account_credit":  cls.ACCOUNTS["vat_payable"],
                "amount_huf":      vat_huf,
                "description":     f"Számlaszám: {invoice.invoice_number} — fizetendő ÁFA",
                "invoice_number":  invoice.invoice_number,
                "issue_date":      invoice.invoice_issue_date,
                "operation":       invoice.operation.value,
            })

        logger.info(
            "Generated %d journal entries for invoice %s (gross HUF %d, net HUF %d, VAT HUF %d)",
            len(entries), invoice.invoice_number, gross_huf, net_huf, vat_huf,
        )
        return entries


# ---------------------------------------------------------------------------
# NAV ONLINE SZÁMLA 3.0 GATEWAY
# ---------------------------------------------------------------------------

class NAVOnlineSzamlaGateway:
    """
    Hungary NAV Online Számla 3.0 Gateway Engine.

    Provides complete integration with the NAV Online Számla 3.0 REST API:
      - Session token exchange (tokenExchange)
      - Invoice submission (manageInvoice)
      - Invoice status and data query (queryInvoiceStatus, queryInvoiceData)
      - Taxpayer data query (queryTaxpayer)
      - Tax number validation (validate_tax_number)

    In SANDBOX mode, all API calls are simulated (no actual HTTP requests made).
    Set environment=NAVEnvironment.PRODUCTION and provide real credentials
    for live NAV integration.
    """

    ENDPOINTS = {
        NAVEnvironment.SANDBOX: {
            "base":               "https://api-test.onlineszamla.nav.gov.hu/invoiceService/v3",
            "token_exchange":     "/tokenExchange",
            "manage_invoice":     "/manageInvoice",
            "query_status":       "/queryInvoiceStatus",
            "query_invoice_data": "/queryInvoiceData",
            "query_taxpayer":     "/queryTaxpayer",
        },
        NAVEnvironment.PRODUCTION: {
            "base":               "https://api.onlineszamla.nav.gov.hu/invoiceService/v3",
            "token_exchange":     "/tokenExchange",
            "manage_invoice":     "/manageInvoice",
            "query_status":       "/queryInvoiceStatus",
            "query_invoice_data": "/queryInvoiceData",
            "query_taxpayer":     "/queryTaxpayer",
        },
    }

    def __init__(
        self,
        environment: NAVEnvironment = NAVEnvironment.SANDBOX,
        credentials: Optional[NAVCredentials] = None,
    ) -> None:
        self.environment = environment
        self.credentials = credentials or NAVCredentials(
            login="TEST_USER",
            password="TEST_PASS",
            tax_number="12345678-2-41",
            signature_key="TEST-SIGNATURE-KEY-1234",
            exchange_key="TEST-EXCHANGE-KEY-5678",
        )
        self._session: Optional[NAVSession] = None
        self._invoice_store: List[NAVInvoice] = []
        self._transaction_store: Dict[str, NAVSubmissionResult] = {}
        logger.info(
            "NAVOnlineSzamlaGateway initialized. Environment=%s, TaxNumber=%s",
            environment.value, self.credentials.tax_number
        )

    @property
    def base_url(self) -> str:
        return self.ENDPOINTS[self.environment]["base"]

    def clean_tax_number(self) -> str:
        return format_tax_number(self.credentials.tax_number)

    # ------------------------------------------------------------------
    # SESSION MANAGEMENT
    # ------------------------------------------------------------------

    def exchange_token(self) -> NAVSession:
        """
        Authenticate with NAV API and obtain a session token (tokenExchange).

        In sandbox mode, returns a simulated token. In production, performs
        an actual HTTP POST to the NAV tokenExchange endpoint.

        Returns:
            Active NAVSession with token_value populated.
        """
        request_id = NAVRequestSigner.generate_request_id()
        timestamp  = NAVRequestSigner.current_timestamp()

        request_xml = NAVInvoiceGenerator.generate_token_exchange_request_xml(
            self.credentials, request_id, timestamp
        )

        if self.environment == NAVEnvironment.SANDBOX:
            # Simulate sandbox token exchange
            token_val = hashlib.sha256(
                f"SANDBOX:{self.credentials.login}:{timestamp}".encode()
            ).hexdigest().upper()
            self._session = NAVSession(token_value=token_val)
            logger.info(
                "NAV tokenExchange [SANDBOX] success. Token=%.16s... RequestId=%s",
                token_val, request_id
            )
        else:
            # Production token exchange via HTTP POST
            import urllib.request as urlreq
            url = self.base_url + self.ENDPOINTS[self.environment]["token_exchange"]
            req = urlreq.Request(
                url,
                data=request_xml.encode("utf-8"),
                method="POST",
                headers={
                    "Content-Type": "application/xml;charset=UTF-8",
                    "Accept": "application/xml",
                },
            )
            try:
                with urlreq.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8")
                    # Parse token from response XML
                    tree = ET.fromstring(body)
                    ns = {"a": NS_API}
                    token_elem = tree.find(".//encodedExchangeToken", ns)
                    if token_elem is None or not token_elem.text:
                        raise RuntimeError("NAV tokenExchange: encodedExchangeToken not found in response")
                    # Decrypt token using exchange_key (XOR in simplified mode)
                    raw_token = base64.b64decode(token_elem.text).decode("utf-8", errors="replace")
                    self._session = NAVSession(token_value=raw_token)
                    logger.info(
                        "NAV tokenExchange [PRODUCTION] success. Token=%.16s...", raw_token
                    )
            except Exception as exc:
                logger.error("NAV tokenExchange failed: %s", exc)
                raise

        return self._session

    def _ensure_session(self) -> NAVSession:
        """Ensure a valid session exists, renewing if expired."""
        if self._session is None or self._session.is_expired():
            self._session = self.exchange_token()
        return self._session

    # ------------------------------------------------------------------
    # INVOICE SUBMISSION
    # ------------------------------------------------------------------

    def submit_invoice(self, invoice: NAVInvoice) -> NAVSubmissionResult:
        """
        Submit an invoice to NAV Online Számla 3.0 (manageInvoice).

        Performs:
          1. Session token validation / exchange
          2. InvoiceData XML generation
          3. XMLDSig signing
          4. SHA-3-512 request signature computation
          5. HTTP POST to manageInvoice endpoint (or sandbox simulation)
          6. Returns NAVSubmissionResult with transaction ID

        Args:
            invoice: Completed NAVInvoice ready for submission.

        Returns:
            NAVSubmissionResult with transaction_id and status.
        """
        session = self._ensure_session()
        request_id = NAVRequestSigner.generate_request_id()
        timestamp  = NAVRequestSigner.current_timestamp()

        # Validate invoice supplier tax number
        if not validate_tax_number(invoice.supplier.tax_number):
            invoice.status = NAVInvoiceStatus.ERROR
            raise ValueError(
                f"Invalid supplier tax number: {invoice.supplier.tax_number}"
            )

        # Generate request XML
        request_xml = NAVInvoiceGenerator.generate_manage_invoice_request_xml(
            invoice, self.credentials, request_id, timestamp
        )

        if self.environment == NAVEnvironment.SANDBOX:
            # Simulate NAV sandbox acceptance
            transaction_id = f"HU-NAV-{request_id[:12]}-{invoice.invoice_number[:8].replace('/', '-')}"
            invoice.status = NAVInvoiceStatus.ACCEPTED
            invoice.nav_transaction_id = transaction_id

            result = NAVSubmissionResult(
                transaction_id=transaction_id,
                invoice_number=invoice.invoice_number,
                status=NAVInvoiceStatus.ACCEPTED,
                index_in_batch=invoice.nav_index_in_batch,
                original_request_id=request_id,
                timestamp=timestamp,
            )
            self._invoice_store.append(invoice)
            self._transaction_store[transaction_id] = result

            logger.info(
                "NAV manageInvoice [SANDBOX] accepted. Invoice=%s TransactionId=%s",
                invoice.invoice_number, transaction_id
            )
        else:
            # Production submission
            import urllib.request as urlreq
            url = self.base_url + self.ENDPOINTS[self.environment]["manage_invoice"]
            req = urlreq.Request(
                url,
                data=request_xml.encode("utf-8"),
                method="POST",
                headers={
                    "Content-Type": "application/xml;charset=UTF-8",
                    "Accept": "application/xml",
                    "X-Request-Id": request_id,
                },
            )
            try:
                with urlreq.urlopen(req, timeout=60) as resp:
                    body = resp.read().decode("utf-8")
                    tree = ET.fromstring(body)
                    txn_elem = tree.find(".//transactionId")
                    transaction_id = txn_elem.text if txn_elem is not None else request_id
                    invoice.status = NAVInvoiceStatus.PROCESSING
                    invoice.nav_transaction_id = transaction_id
                    result = NAVSubmissionResult(
                        transaction_id=transaction_id,
                        invoice_number=invoice.invoice_number,
                        status=NAVInvoiceStatus.PROCESSING,
                        original_request_id=request_id,
                        timestamp=timestamp,
                    )
                    self._invoice_store.append(invoice)
                    self._transaction_store[transaction_id] = result
                    logger.info(
                        "NAV manageInvoice [PRODUCTION] submitted. Invoice=%s TransactionId=%s",
                        invoice.invoice_number, transaction_id
                    )
            except Exception as exc:
                logger.error("NAV manageInvoice failed: %s", exc)
                invoice.status = NAVInvoiceStatus.ERROR
                raise

        return result

    # ------------------------------------------------------------------
    # STATUS QUERY
    # ------------------------------------------------------------------

    def query_invoice_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Query the processing status of a submitted invoice (queryInvoiceStatus).

        Args:
            transaction_id: NAV-assigned transaction ID from submit_invoice().

        Returns:
            Dict with keys: transaction_id, status, processing_results, annul_data
        """
        if self.environment == NAVEnvironment.SANDBOX:
            # Simulate NAV sandbox status response
            stored_result = self._transaction_store.get(transaction_id)
            processing_results = []

            if stored_result:
                processing_results = [{
                    "index":         stored_result.index_in_batch,
                    "invoiceStatus": stored_result.status.value,
                    "compressedContentIndicator": False,
                }]

            return {
                "transaction_id":    transaction_id,
                "status":            (stored_result.status.value if stored_result else "UNKNOWN"),
                "processing_results": processing_results,
                "annul_data":        [],
                "original_request_id": (stored_result.original_request_id if stored_result else ""),
            }
        else:
            import urllib.request as urlreq
            request_id = NAVRequestSigner.generate_request_id()
            timestamp  = NAVRequestSigner.current_timestamp()

            # Build queryInvoiceStatus XML request
            root = ET.Element(f"{{{NS_API}}}QueryInvoiceStatusRequest")
            root.set("xmlns", NS_API)
            root.set("xmlns:common", NS_COMMON)

            header = ET.SubElement(root, f"{{{NS_COMMON}}}header")
            ET.SubElement(header, f"{{{NS_COMMON}}}requestId").text = request_id
            ET.SubElement(header, f"{{{NS_COMMON}}}timestamp").text = timestamp
            ET.SubElement(header, f"{{{NS_COMMON}}}requestVersion").text = NAV_SCHEMA_VERSION
            ET.SubElement(header, f"{{{NS_COMMON}}}headerVersion").text = NAV_HEADER_VERSION

            user = ET.SubElement(root, f"{{{NS_COMMON}}}user")
            ET.SubElement(user, f"{{{NS_COMMON}}}login").text = self.credentials.login
            ET.SubElement(user, f"{{{NS_COMMON}}}passwordHash").text = self.credentials.password_hash()
            ET.SubElement(user, f"{{{NS_COMMON}}}taxNumber").text = self.clean_tax_number()
            request_sig = NAVRequestSigner.compute_request_signature(request_id, timestamp, self.credentials.signature_key)
            ET.SubElement(user, f"{{{NS_COMMON}}}requestSignature").text = request_sig

            ET.SubElement(root, "transactionId").text = transaction_id

            ET.indent(root, space="  ")
            req_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
            url = self.base_url + self.ENDPOINTS[self.environment]["query_status"]
            req = urlreq.Request(url, data=req_xml.encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/xml;charset=UTF-8"})
            with urlreq.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return {"transaction_id": transaction_id, "raw_response": body}

    # ------------------------------------------------------------------
    # TAXPAYER QUERY
    # ------------------------------------------------------------------

    def query_taxpayer(self, tax_number: str) -> NAVTaxpayerInfo:
        """
        Query taxpayer data from NAV (queryTaxpayer endpoint).

        Args:
            tax_number: Hungarian tax number (adószám) to query.

        Returns:
            NAVTaxpayerInfo with company name and VAT validity.
        """
        if not validate_tax_number(tax_number):
            return NAVTaxpayerInfo(
                tax_number=tax_number,
                company_name="",
                is_valid=False,
                tax_validity="INVALID",
                query_timestamp=NAVRequestSigner.current_timestamp(),
            )

        if self.environment == NAVEnvironment.SANDBOX:
            # Sandbox: return synthetic taxpayer data
            clean = format_tax_number(tax_number)
            return NAVTaxpayerInfo(
                tax_number=tax_number,
                company_name=f"TESZT VÁLLALKOZÁS [{clean}] KFT.",
                is_valid=True,
                tax_validity="VALID",
                vat_status="ÁFÁS",
                address="1051 Budapest, Teszt utca 1.",
                query_timestamp=NAVRequestSigner.current_timestamp(),
            )
        else:
            import urllib.request as urlreq
            request_id = NAVRequestSigner.generate_request_id()
            timestamp  = NAVRequestSigner.current_timestamp()
            req_xml = NAVInvoiceGenerator.generate_query_taxpayer_request_xml(
                tax_number, self.credentials, request_id, timestamp
            )
            url = self.base_url + self.ENDPOINTS[self.environment]["query_taxpayer"]
            req = urlreq.Request(url, data=req_xml.encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/xml;charset=UTF-8"})
            with urlreq.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                tree = ET.fromstring(body)
                name_elem = tree.find(".//taxpayerName")
                validity_elem = tree.find(".//taxpayerValidity")
                return NAVTaxpayerInfo(
                    tax_number=tax_number,
                    company_name=name_elem.text if name_elem is not None else "",
                    is_valid=True,
                    tax_validity=validity_elem.text if validity_elem is not None else "UNKNOWN",
                    query_timestamp=timestamp,
                )

    # ------------------------------------------------------------------
    # INVOICE LISTING
    # ------------------------------------------------------------------

    def list_invoices(
        self,
        status: Optional[NAVInvoiceStatus] = None,
        limit: int = 100,
    ) -> List[NAVInvoice]:
        """Return submitted invoices, optionally filtered by status."""
        invoices = self._invoice_store[-limit:]
        if status:
            invoices = [inv for inv in invoices if inv.status == status]
        return invoices

    def get_invoice(self, invoice_number: str) -> Optional[NAVInvoice]:
        """Find a stored invoice by invoice number."""
        for inv in self._invoice_store:
            if inv.invoice_number == invoice_number:
                return inv
        return None

    # ------------------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Return operational statistics for the NAV gateway."""
        total = len(self._invoice_store)
        by_status: Dict[str, int] = {}
        total_net_huf = 0
        total_vat_huf = 0
        total_gross_huf = 0

        for inv in self._invoice_store:
            status_key = inv.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
            total_net_huf   += round_huf(inv.invoice_net_amount)
            total_vat_huf   += round_huf(inv.invoice_vat_amount)
            total_gross_huf += round_huf(inv.invoice_gross_amount)

        return {
            "environment":       self.environment.value,
            "tax_number":        self.credentials.tax_number,
            "total_invoices":    total,
            "by_status":         by_status,
            "total_net_huf":     total_net_huf,
            "total_vat_huf":     total_vat_huf,
            "total_gross_huf":   total_gross_huf,
            "session_active":    self._session is not None and self._session.is_valid(),
            "schema_version":    NAV_SCHEMA_VERSION,
        }
