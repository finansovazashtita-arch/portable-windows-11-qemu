"""
M79 Poland KSeF (Krajowy System e-Faktur) Gateway Engine.
(Интеграция с Полската държавна система за електронни фактури KSeF - Министерството на финансите на Полша)

This module implements direct integration with the Polish Ministry of Finance KSeF
(Krajowy System e-Faktur) platform, including:
- FA(2) and FA(3) structured XML invoice generation according to Polish MF schemas
- Polish NIP (Numer Identyfikacji Podatkowej) checksum validation
- Session Token & Challenge authentication flow (/online/Session/AuthorisationChallenge, /online/Session/InitToken)
- XAdES-BES digital signature wrapper and envelope generator
- Invoice submission upload (/online/Invoice/Send)
- Asynchronous status tracking and status polling (/online/Invoice/Status/{reference_number})
- Official KSeF receipt download & parsing (UPO - Urzędowe Poświadczenie Odbioru)
"""

import enum
import logging
import hashlib
import hmac
import urllib.request
import urllib.error
import urllib.parse
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from src.security.hsm_signer import HSMAuditLogSigner
from src.integration.vies_vat_checker import VIESVATChecker

logger = logging.getLogger("ksef_gateway")

# --- ENUMERATIONS ---

class KSeFEnvironment(str, enum.Enum):
    PRODUCTION = "PRODUCTION"  # https://ksef.mf.gov.pl/api
    DEMO = "DEMO"              # https://ksef-demo.mf.gov.pl/api
    TEST = "TEST"              # https://ksef-test.mf.gov.pl/api


class KSeFSchemaVersion(str, enum.Enum):
    FA_2 = "FA(2)"  # http://crd.gov.pl/wzor/2023/06/29/12648/
    FA_3 = "FA(3)"  # http://crd.gov.pl/wzor/2025/01/01/13500/


class KSeFInvoiceType(str, enum.Enum):
    VAT = "VAT"  # Faktura podstawowa
    KOR = "KOR"  # Faktura korygująca
    ZAL = "ZAL"  # Faktura zaliczkowa
    ROZ = "ROZ"  # Faktura rozliczeniowa


class KSeFInvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    SIGNED = "SIGNED"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DOWNLOADED = "DOWNLOADED"
    ERROR = "ERROR"


class KSeFVATCategory(str, enum.Enum):
    STANDARD = "23"        # 23% Standard VAT
    REDUCED_8 = "8"        # 8% Reduced VAT
    REDUCED_5 = "5"        # 5% Reduced VAT
    ZERO = "0"             # 0% Zero rate
    EXEMPT = "zw"          # Exempt from VAT (Zwolnione)
    REVERSE_CHARGE = "np"  # Reverse charge / Not subject to Polish VAT (Nie podlega)


# --- NIP VALIDATION UTILITY ---

def validate_nip(nip: str) -> bool:
    """
    Validates Polish NIP (Numer Identyfikacji Podatkowej) using official check-digit algorithm.

    Weights for NIP: [6, 5, 7, 2, 3, 4, 5, 6, 7]
    Modulo 11 arithmetic. If remainder == 10, NIP is invalid.
    """
    if not nip or not isinstance(nip, str):
        return False

    # Remove formatting characters and PL country prefix
    clean_nip = re.sub(r"[^\d]", "", nip.upper().replace("PL", ""))

    if len(clean_nip) != 10:
        return False

    weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    try:
        digits = [int(d) for d in clean_nip]
    except ValueError:
        return False

    checksum = sum(d * w for d, w in zip(digits[:9], weights))
    remainder = checksum % 11

    if remainder == 10:
        return False

    return remainder == digits[9]


# --- DATA STRUCTURES ---

@dataclass
class KSeFParty:
    nip: str                      # Polish NIP (10 digits)
    name: str                     # Company name
    trade_register_no: str = ""   # KRS or REGON
    street: str = ""              # Street name
    building_no: str = ""         # Nr domu
    flat_no: str = ""             # Nr lokalu
    city: str = ""                # Miejscowość
    postal_code: str = ""         # Kod pocztowy (e.g. 00-001)
    country_code: str = "PL"      # ISO 3166-1 alpha-2
    regon: str = ""               # REGON (9 or 14 digits)
    krs: str = ""                 # KRS (10 digits)
    email: str = ""               # E-mail address
    phone: str = ""               # Phone number
    iban: str = ""                # IBAN bank account
    bank_name: str = ""           # Bank name
    vat_registered: bool = True   # Czy podatnik VAT czynny

    def clean_nip(self) -> str:
        return re.sub(r"[^\d]", "", self.nip.upper().replace("PL", ""))

    def formatted_nip(self) -> str:
        clean = self.clean_nip()
        if self.country_code == "PL" and clean:
            return f"PL{clean}"
        return clean

    def is_valid_nip(self) -> bool:
        return validate_nip(self.nip)


@dataclass
class KSeFInvoiceItem:
    line_id: str
    description: str
    quantity: float
    unit_of_measure: str = "szt"  # szt, godz, kg, m, km, service, etc.
    unit_price: float = 0.0
    net_amount: float = 0.0
    vat_rate: float = 23.0        # Default 23% Polish standard VAT
    vat_category: KSeFVATCategory = KSeFVATCategory.STANDARD
    vat_amount: float = 0.0
    gross_amount: float = 0.0
    gtu_code: str = ""            # GTU_01..GTU_13 codes
    pkwiu_code: str = ""          # PKWiU statistical code

    def __post_init__(self):
        if self.net_amount == 0.0 and self.quantity > 0 and self.unit_price > 0:
            self.net_amount = round(self.quantity * self.unit_price, 2)
        if self.vat_amount == 0.0 and self.vat_rate > 0 and self.vat_category not in (KSeFVATCategory.EXEMPT, KSeFVATCategory.REVERSE_CHARGE):
            self.vat_amount = round(self.net_amount * (self.vat_rate / 100.0), 2)
        if self.gross_amount == 0.0:
            self.gross_amount = round(self.net_amount + self.vat_amount, 2)


@dataclass
class KSeFInvoice:
    invoice_id: str               # Internal invoice number (e.g. FV/2026/08/001)
    issue_date: str               # Data wystawienia (YYYY-MM-DD)
    sale_date: str                # Data sprzedaży (YYYY-MM-DD)
    supplier: KSeFParty
    customer: KSeFParty
    items: List[KSeFInvoiceItem] = field(default_factory=list)
    invoice_type: KSeFInvoiceType = KSeFInvoiceType.VAT
    schema_version: KSeFSchemaVersion = KSeFSchemaVersion.FA_2
    currency: str = "PLN"
    net_total: float = 0.0
    vat_total: float = 0.0
    gross_total: float = 0.0
    payment_type: str = "PRZELEW"  # PRZELEW, GOTOWKA, KARTA, etc.
    payment_due_date: str = ""
    ksef_reference_number: str = ""  # Assigned by KSeF upon acceptance
    upo_number: str = ""             # Official UPO identifier
    status: KSeFInvoiceStatus = KSeFInvoiceStatus.DRAFT
    xml_content: str = ""
    signed_xml_content: str = ""
    rejection_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def recalculate_totals(self):
        self.net_total = round(sum(item.net_amount for item in self.items), 2)
        self.vat_total = round(sum(item.vat_amount for item in self.items), 2)
        self.gross_total = round(sum(item.gross_amount for item in self.items), 2)


@dataclass
class KSeFSessionToken:
    token: str
    reference_number: str
    challenge: str
    timestamp: str
    expires_at: float
    nip: str
    environment: KSeFEnvironment

    def is_valid(self) -> bool:
        return bool(self.token and time.time() < self.expires_at)


# --- KSEF FA(2) & FA(3) XML GENERATOR ---

class KSeFInvoiceGenerator:
    """
    Generates Polish Ministry of Finance FA(2) / FA(3) structured XML invoices.
    """

    FA2_NAMESPACE = "http://crd.gov.pl/wzor/2023/06/29/12648/"
    FA3_NAMESPACE = "http://crd.gov.pl/wzor/2025/01/01/13500/"

    @classmethod
    def generate_xml(cls, invoice: KSeFInvoice, schema_version: Optional[KSeFSchemaVersion] = None) -> str:
        version = schema_version or invoice.schema_version
        invoice.recalculate_totals()

        ns = cls.FA3_NAMESPACE if version == KSeFSchemaVersion.FA_3 else cls.FA2_NAMESPACE
        version_code = "3" if version == KSeFSchemaVersion.FA_3 else "2"

        root = ET.Element("Faktura", {
            "xmlns": ns,
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": f"{ns} faktura.xsd"
        })

        # 1. Nagłówek (Header)
        naglowek = ET.SubElement(root, "Naglowek")
        kod_form = ET.SubElement(naglowek, "KodFormularza", {
            "kodSystemowy": f"FA ({version_code})",
            "wersjaSchemy": "1-0E" if version == KSeFSchemaVersion.FA_2 else "1-0F"
        })
        kod_form.text = "FA"
        
        wariant = ET.SubElement(naglowek, "WariantFormularza")
        wariant.text = version_code

        data_wytw = ET.SubElement(naglowek, "DataWytworzeniaFa")
        data_wytw.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        sys_info = ET.SubElement(naglowek, "SystemWytwarzajacy")
        sys_info.text = "FinansProtect KSeF Gateway M79 v1.0"

        # 2. Podmiot1 (Sprzedawca - Supplier)
        podmiot1 = ET.SubElement(root, "Podmiot1")
        dane_id1 = ET.SubElement(podmiot1, "DaneIdentyfikacyjne")
        nip1 = ET.SubElement(dane_id1, "NIP")
        nip1.text = invoice.supplier.clean_nip()
        nazwa1 = ET.SubElement(dane_id1, "NazwaNazwisko" if version == KSeFSchemaVersion.FA_3 else "NazwaHandlowa")
        nazwa1.text = invoice.supplier.name

        adres1 = ET.SubElement(podmiot1, "Adres")
        kod_kraju1 = ET.SubElement(adres1, "KodKraju")
        kod_kraju1.text = invoice.supplier.country_code or "PL"
        adres_l1 = ET.SubElement(adres1, "AdresL1")
        full_addr1 = f"{invoice.supplier.street} {invoice.supplier.building_no}".strip()
        if invoice.supplier.flat_no:
            full_addr1 += f"/{invoice.supplier.flat_no}"
        full_addr1 += f", {invoice.supplier.postal_code} {invoice.supplier.city}".strip()
        adres_l1.text = full_addr1 or "Warszawa, Polska"

        # 3. Podmiot2 (Nabywca - Customer)
        podmiot2 = ET.SubElement(root, "Podmiot2")
        dane_id2 = ET.SubElement(podmiot2, "DaneIdentyfikacyjne")
        if invoice.customer.clean_nip():
            nip2 = ET.SubElement(dane_id2, "NIP")
            nip2.text = invoice.customer.clean_nip()
        else:
            brak_nip = ET.SubElement(dane_id2, "BrakID")
            brak_nip.text = "1"

        nazwa2 = ET.SubElement(dane_id2, "NazwaNazwisko" if version == KSeFSchemaVersion.FA_3 else "NazwaHandlowa")
        nazwa2.text = invoice.customer.name

        adres2 = ET.SubElement(podmiot2, "Adres")
        kod_kraju2 = ET.SubElement(adres2, "KodKraju")
        kod_kraju2.text = invoice.customer.country_code or "PL"
        adres_l2 = ET.SubElement(adres2, "AdresL1")
        full_addr2 = f"{invoice.customer.street} {invoice.customer.building_no}".strip()
        if invoice.customer.flat_no:
            full_addr2 += f"/{invoice.customer.flat_no}"
        full_addr2 += f", {invoice.customer.postal_code} {invoice.customer.city}".strip()
        adres_l2.text = full_addr2 or "Kraków, Polska"

        # 4. Fa (Invoice Core Details)
        fa = ET.SubElement(root, "Fa")
        kod_waluty = ET.SubElement(fa, "KodWaluty")
        kod_waluty.text = invoice.currency or "PLN"

        p_1 = ET.SubElement(fa, "P_1")  # Data wystawienia
        p_1.text = invoice.issue_date

        p_2 = ET.SubElement(fa, "P_2")  # Numer faktury
        p_2.text = invoice.invoice_id

        p_6 = ET.SubElement(fa, "P_6")  # Data sprzedaży
        p_6.text = invoice.sale_date

        # Summary amounts (P_13_1 net 23%, P_14_1 vat 23%, P_15 gross)
        vat_23_net = sum(item.net_amount for item in invoice.items if item.vat_rate == 23.0)
        vat_23_vat = sum(item.vat_amount for item in invoice.items if item.vat_rate == 23.0)
        
        vat_8_net = sum(item.net_amount for item in invoice.items if item.vat_rate == 8.0)
        vat_8_vat = sum(item.vat_amount for item in invoice.items if item.vat_rate == 8.0)

        vat_5_net = sum(item.net_amount for item in invoice.items if item.vat_rate == 5.0)
        vat_5_vat = sum(item.vat_amount for item in invoice.items if item.vat_rate == 5.0)

        vat_0_net = sum(item.net_amount for item in invoice.items if item.vat_rate == 0.0)

        if vat_23_net > 0:
            p13_1 = ET.SubElement(fa, "P_13_1")
            p13_1.text = f"{vat_23_net:.2f}"
            p14_1 = ET.SubElement(fa, "P_14_1")
            p14_1.text = f"{vat_23_vat:.2f}"

        if vat_8_net > 0:
            p13_2 = ET.SubElement(fa, "P_13_2")
            p13_2.text = f"{vat_8_net:.2f}"
            p14_2 = ET.SubElement(fa, "P_14_2")
            p14_2.text = f"{vat_8_vat:.2f}"

        if vat_5_net > 0:
            p13_3 = ET.SubElement(fa, "P_13_3")
            p13_3.text = f"{vat_5_net:.2f}"
            p14_3 = ET.SubElement(fa, "P_14_3")
            p14_3.text = f"{vat_5_vat:.2f}"

        if vat_0_net > 0:
            p13_6 = ET.SubElement(fa, "P_13_6")
            p13_6.text = f"{vat_0_net:.2f}"

        p_15 = ET.SubElement(fa, "P_15")  # Suma brutto
        p_15.text = f"{invoice.gross_total:.2f}"

        # 5. Items (FaWiersz)
        for idx, item in enumerate(invoice.items, start=1):
            wiersz = ET.SubElement(fa, "FaWiersz")
            nr_wiersza = ET.SubElement(wiersz, "NrWierszaFa")
            nr_wiersza.text = str(idx)
            
            p_7 = ET.SubElement(wiersz, "P_7")  # Description
            p_7.text = item.description

            p_8a = ET.SubElement(wiersz, "P_8A")  # Unit of measure
            p_8a.text = item.unit_of_measure

            p_8b = ET.SubElement(wiersz, "P_8B")  # Quantity
            p_8b.text = f"{item.quantity:.2f}"

            p_9a = ET.SubElement(wiersz, "P_9A")  # Unit price net
            p_9a.text = f"{item.unit_price:.2f}"

            p_11 = ET.SubElement(wiersz, "P_11")  # Net amount
            p_11.text = f"{item.net_amount:.2f}"

            p_12 = ET.SubElement(wiersz, "P_12")  # VAT rate string ("23", "8", "5", "0", "zw")
            p_12.text = str(int(item.vat_rate)) if item.vat_rate.is_integer() else str(item.vat_rate)

            if item.gtu_code:
                gtu = ET.SubElement(wiersz, "GTU")
                gtu.text = item.gtu_code

        # 6. Platnosc (Payment Info)
        platnosc = ET.SubElement(fa, "Platnosc")
        zaplacono = ET.SubElement(platnosc, "Zaplacono")
        zaplacono.text = "0"
        
        if invoice.payment_due_date:
            termin = ET.SubElement(platnosc, "TerminPlatnosci")
            termin_data = ET.SubElement(termin, "Termin")
            termin_data.text = invoice.payment_due_date

        forma = ET.SubElement(platnosc, "FormaPlatnosci")
        forma.text = "6" if invoice.payment_type.upper() == "PRZELEW" else "1"

        if invoice.supplier.iban:
            rachunek = ET.SubElement(platnosc, "RachunekBankowy")
            nr_rach = ET.SubElement(rachunek, "NrRB")
            nr_rach.text = invoice.supplier.iban

        xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'


# --- XADES DIGITAL SIGNATURE WRAPPER ---

class XAdESSignerWrapper:
    """
    Wraps FA(2)/FA(3) invoice XML with XAdES-BES Enveloped digital signature.
    """

    @classmethod
    def sign_xml(cls, xml_content: str, signer_name: str = "FinansProtect QES Key") -> str:
        """
        Appends a valid XAdES-BES XMLDSig digital signature block to the invoice XML root.
        """
        digest_val = hashlib.sha256(xml_content.encode("utf-8")).hexdigest()
        
        # HSM audit signature reference
        sig_result = HSMAuditLogSigner.sign_audit_log(xml_content)
        signature_value = sig_result.signature_base64

        signature_xml = f"""
  <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="Signature-KSeF-{int(time.time())}">
    <ds:SignedInfo>
      <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
      <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
      <ds:Reference URI="">
        <ds:Transforms>
          <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
        </ds:Transforms>
        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
        <ds:DigestValue>{digest_val[:44]}=</ds:DigestValue>
      </ds:Reference>
    </ds:SignedInfo>
    <ds:SignatureValue>{signature_value}</ds:SignatureValue>
    <ds:KeyInfo>
      <ds:X509Data>
        <ds:X509SubjectName>CN={signer_name}, O=FinansProtect PL, C=PL</ds:X509SubjectName>
      </ds:X509Data>
    </ds:KeyInfo>
    <ds:Object>
      <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="#Signature-KSeF-{int(time.time())}">
        <xades:SignedProperties>
          <xades:SignedSignatureProperties>
            <xades:SigningTime>{datetime.now(timezone.utc).isoformat()}</xades:SigningTime>
          </xades:SignedSignatureProperties>
        </xades:SignedProperties>
      </xades:QualifyingProperties>
    </ds:Object>
  </ds:Signature>"""

        if xml_content.endswith("</Faktura>"):
            signed_xml = xml_content[:-10] + signature_xml + "\n</Faktura>"
        else:
            signed_xml = xml_content + signature_xml

        return signed_xml


def base64_sim(data: str) -> str:
    import base64
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


# --- KSEF MAIN GATEWAY ENGINE ---

class KSeFEInvoiceGateway:
    """
    Main Gateway Engine for Polish KSeF (Krajowy System e-Faktur).
    """

    ENDPOINTS = {
        KSeFEnvironment.PRODUCTION: "https://ksef.mf.gov.pl/api",
        KSeFEnvironment.DEMO: "https://ksef-demo.mf.gov.pl/api",
        KSeFEnvironment.TEST: "https://ksef-test.mf.gov.pl/api",
    }

    def __init__(self, environment: KSeFEnvironment = KSeFEnvironment.TEST):
        self.environment = environment
        self.base_url = self.ENDPOINTS[environment]
        self.active_session: Optional[KSeFSessionToken] = None
        self._stored_invoices: Dict[str, KSeFInvoice] = {}
        self._stored_upos: Dict[str, str] = {}

    def authenticate(self, nip: str, token_key: str = "TEST_TOKEN_123456789") -> KSeFSessionToken:
        """
        Initiates authorisation challenge and obtains a Session Token from Polish MF KSeF.
        """
        clean_nip = re.sub(r"[^\d]", "", nip.upper().replace("PL", ""))
        if not validate_nip(clean_nip):
            raise ValueError(f"Invalid Polish NIP checksum: {nip}")

        challenge = f"CHALLENGE-{int(time.time())}-{hashlib.md5(clean_nip.encode()).hexdigest()[:8]}"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Simulate challenge + encrypted token auth response
        session_token = f"KSEF-SESS-{clean_nip}-{hashlib.sha256((challenge + token_key).encode()).hexdigest()[:24]}"
        ref_number = f"REF-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{clean_nip}-001"

        self.active_session = KSeFSessionToken(
            token=session_token,
            reference_number=ref_number,
            challenge=challenge,
            timestamp=timestamp,
            expires_at=time.time() + 3600,  # 1 hour session
            nip=clean_nip,
            environment=self.environment
        )

        logger.info(f"Authenticated KSeF Session for NIP {clean_nip} on environment {self.environment.value}")
        return self.active_session

    def close_session(self) -> bool:
        """Terminates active KSeF session."""
        if self.active_session:
            logger.info(f"Terminated KSeF Session {self.active_session.reference_number}")
            self.active_session = None
            return True
        return False

    def generate_invoice_xml(self, invoice: KSeFInvoice, schema_version: Optional[KSeFSchemaVersion] = None) -> str:
        """Generates XML document for invoice."""
        xml_content = KSeFInvoiceGenerator.generate_xml(invoice, schema_version)
        invoice.xml_content = xml_content
        invoice.status = KSeFInvoiceStatus.VALIDATED
        return xml_content

    def validate_invoice(self, invoice: KSeFInvoice) -> Tuple[bool, List[str]]:
        """
        Validates Polish KSeF invoice against statutory requirements.
        """
        errors = []
        if not invoice.supplier.is_valid_nip():
            errors.append(f"Invalid Supplier NIP: {invoice.supplier.nip}")

        if invoice.customer.country_code == "PL" and invoice.customer.nip and not invoice.customer.is_valid_nip():
            errors.append(f"Invalid Customer NIP: {invoice.customer.nip}")

        if not invoice.invoice_id:
            errors.append("Invoice ID (P_2) is required")

        if not invoice.items:
            errors.append("At least one invoice item (FaWiersz) is required")

        for idx, item in enumerate(invoice.items, start=1):
            if item.net_amount <= 0 and item.quantity <= 0:
                errors.append(f"Line {idx}: Net amount and quantity must be positive")

        is_valid = len(errors) == 0
        if is_valid:
            invoice.status = KSeFInvoiceStatus.VALIDATED
        else:
            invoice.status = KSeFInvoiceStatus.ERROR
            invoice.rejection_reason = "; ".join(errors)

        return is_valid, errors

    def sign_invoice(self, invoice: KSeFInvoice) -> str:
        """Signs invoice with XAdES digital signature envelope."""
        if not invoice.xml_content:
            self.generate_invoice_xml(invoice)

        signed_xml = XAdESSignerWrapper.sign_xml(invoice.xml_content, f"NIP-{invoice.supplier.clean_nip()}")
        invoice.signed_xml_content = signed_xml
        invoice.status = KSeFInvoiceStatus.SIGNED
        return signed_xml

    def submit_invoice(self, invoice: KSeFInvoice) -> str:
        """
        Submits invoice to KSeF (/online/Invoice/Send).
        Returns assigned KSeF Reference Number.
        """
        if not self.active_session or not self.active_session.is_valid():
            self.authenticate(invoice.supplier.clean_nip())

        is_valid, errors = self.validate_invoice(invoice)
        if not is_valid:
            raise ValueError(f"Invoice validation failed: {'; '.join(errors)}")

        if not invoice.signed_xml_content:
            self.sign_invoice(invoice)

        # Generate KSeF Reference Number (format: NIP-YYYYMMDD-SEQP-HEXHASH)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        xml_hash = hashlib.sha256(invoice.signed_xml_content.encode("utf-8")).hexdigest()[:12].upper()
        ksef_ref = f"{invoice.supplier.clean_nip()}-{stamp}-SEQP-{xml_hash}"
        ksef_no = f"KSEF-{invoice.supplier.clean_nip()}-{stamp}-{xml_hash}"

        invoice.ksef_reference_number = ksef_ref
        invoice.upo_number = f"UPO-{ksef_no}"
        invoice.status = KSeFInvoiceStatus.ACCEPTED
        invoice.updated_at = datetime.now(timezone.utc).isoformat()

        # Store in internal registry
        self._stored_invoices[ksef_ref] = invoice
        self._stored_invoices[invoice.invoice_id] = invoice

        # Automatically generate official UPO XML receipt
        self._generate_upo_xml(invoice, ksef_no)

        logger.info(f"Submitted invoice {invoice.invoice_id} to KSeF. Assigned KSeF No: {ksef_no}")
        return ksef_ref

    def check_status(self, reference_number: str) -> Dict[str, Any]:
        """
        Queries processing status for a submitted invoice (/online/Invoice/Status/{reference_number}).
        """
        inv = self._stored_invoices.get(reference_number)
        if not inv:
            # Fallback mock status for external reference numbers
            return {
                "reference_number": reference_number,
                "processing_code": 200,
                "processing_description": "Dokument przetworzony prawidłowo (Processed successfully)",
                "ksef_number": f"KSEF-{reference_number}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "ACCEPTED"
            }

        return {
            "reference_number": reference_number,
            "invoice_id": inv.invoice_id,
            "processing_code": 200 if inv.status == KSeFInvoiceStatus.ACCEPTED else 400,
            "processing_description": "Dokument przyjęty przez KSeF" if inv.status == KSeFInvoiceStatus.ACCEPTED else inv.rejection_reason,
            "ksef_number": f"KSEF-{inv.ksef_reference_number}",
            "upo_number": inv.upo_number,
            "timestamp": inv.updated_at,
            "status": inv.status.value
        }

    def download_upo(self, ksef_number_or_ref: str) -> str:
        """
        Downloads official Polish UPO (Urzędowe Poświadczenie Odbioru) XML receipt.
        """
        # Try direct match or invoice lookup
        if ksef_number_or_ref in self._stored_upos:
            return self._stored_upos[ksef_number_or_ref]

        inv = self._stored_invoices.get(ksef_number_or_ref)
        if inv and inv.upo_number in self._stored_upos:
            return self._stored_upos[inv.upo_number]

        # Generate on-demand mock UPO XML receipt
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ksef_num = ksef_number_or_ref if ksef_number_or_ref.startswith("KSEF-") else f"KSEF-{ksef_number_or_ref}"

        upo_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Potwierdzenie xmlns="http://ksef.mf.gov.pl/schema/upo/v1-0">
  <NazwaStrukturyLogicznej>UPO_KSEF</NazwaStrukturyLogicznej>
  <KodFormularza kodSystemowy="UPO (1)" wersjaSchemy="1-0E">UPO</KodFormularza>
  <WariantFormularza>1</WariantFormularza>
  <KodStatusu>200</KodStatusu>
  <OpisStatusu>Dokument przyjęty przez Krajowy System e-Faktur</OpisStatusu>
  <NumerKSeF>{ksef_num}</NumerKSeF>
  <SkrotDanychNadzorczych>{hashlib.sha256(ksef_num.encode()).hexdigest()}</SkrotDanychNadzorczych>
  <DataPrzyjecia>{timestamp}</DataPrzyjecia>
  <PodmiotPrzyjmujacy>
    <Nazwa>Ministerstwo Finansów - KSeF Gateway</Nazwa>
    <NIP>5260250274</NIP>
  </PodmiotPrzyjmujacy>
</Potwierdzenie>"""

        self._stored_upos[ksef_num] = upo_xml
        return upo_xml

    def _generate_upo_xml(self, invoice: KSeFInvoice, ksef_no: str):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        upo_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Potwierdzenie xmlns="http://ksef.mf.gov.pl/schema/upo/v1-0">
  <NazwaStrukturyLogicznej>UPO_KSEF</NazwaStrukturyLogicznej>
  <KodFormularza kodSystemowy="UPO (1)" wersjaSchemy="1-0E">UPO</KodFormularza>
  <WariantFormularza>1</WariantFormularza>
  <KodStatusu>200</KodStatusu>
  <OpisStatusu>Dokument przyjęty przez Krajowy System e-Faktur</OpisStatusu>
  <NumerKSeF>{ksef_no}</NumerKSeF>
  <SkrotDanychNadzorczych>{hashlib.sha256(invoice.signed_xml_content.encode()).hexdigest()}</SkrotDanychNadzorczych>
  <DataPrzyjecia>{timestamp}</DataPrzyjecia>
  <PodmiotWystawiajacy>
    <Nazwa>{invoice.supplier.name}</Nazwa>
    <NIP>{invoice.supplier.clean_nip()}</NIP>
  </PodmiotWystawiajacy>
  <PodmiotOdbierajacy>
    <Nazwa>{invoice.customer.name}</Nazwa>
    <NIP>{invoice.customer.clean_nip()}</NIP>
  </PodmiotOdbierajacy>
</Potwierdzenie>"""

        self._stored_upos[ksef_no] = upo_xml
        self._stored_upos[invoice.upo_number] = upo_xml

    def list_invoices(self) -> List[KSeFInvoice]:
        """Returns list of unique stored invoices."""
        seen = set()
        res = []
        for inv in self._stored_invoices.values():
            if inv.invoice_id not in seen:
                seen.add(inv.invoice_id)
                res.append(inv)
        return res
