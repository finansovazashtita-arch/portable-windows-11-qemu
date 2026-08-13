"""
Unit & Integration Test Suite for Poland KSeF Gateway Engine (M79).
"""

import pytest
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from src.integration.ksef_gateway import (
    KSeFEInvoiceGateway,
    KSeFInvoiceGenerator,
    XAdESSignerWrapper,
    KSeFInvoice,
    KSeFParty,
    KSeFInvoiceItem,
    KSeFInvoiceType,
    KSeFSchemaVersion,
    KSeFInvoiceStatus,
    KSeFVATCategory,
    KSeFEnvironment,
    validate_nip
)


def test_nip_validation():
    # Valid Polish NIPs
    assert validate_nip("5260250274") is True   # MF PL
    assert validate_nip("PL5260250274") is True
    assert validate_nip("5252389023") is True   # Allegro
    assert validate_nip("7792400019") is True   # CD Projekt
    assert validate_nip("5260215088") is True   # PKO BP

    # Invalid Polish NIPs
    assert validate_nip("1234567890") is False  # Invalid check digit
    assert validate_nip("5260250275") is False
    assert validate_nip("123") is False
    assert validate_nip("") is False
    assert validate_nip(None) is False


def test_ksef_party_methods():
    supplier = KSeFParty(
        nip="PL 526-025-02-74",
        name="MF PL",
        country_code="PL"
    )
    assert supplier.clean_nip() == "5260250274"
    assert supplier.formatted_nip() == "PL5260250274"
    assert supplier.is_valid_nip() is True


def test_fa2_xml_generation():
    supplier = KSeFParty(nip="5260250274", name="Sprzedawca Sp. z o.o.", street="ul. Główna 1", city="Warszawa", postal_code="00-001")
    customer = KSeFParty(nip="5252389023", name="Nabywca S.A.", street="ul. Grunwaldzka 182", city="Poznań", postal_code="60-166")
    
    item = KSeFInvoiceItem(
        line_id="1",
        description="Usługa IT",
        quantity=2.0,
        unit_price=1000.0,
        vat_rate=23.0
    )

    invoice = KSeFInvoice(
        invoice_id="FV/2026/01",
        issue_date="2026-08-13",
        sale_date="2026-08-13",
        supplier=supplier,
        customer=customer,
        items=[item],
        schema_version=KSeFSchemaVersion.FA_2
    )

    xml_str = KSeFInvoiceGenerator.generate_xml(invoice)
    assert "<?xml version=" in xml_str
    assert "http://crd.gov.pl/wzor/2023/06/29/12648/" in xml_str
    assert "FA (2)" in xml_str
    assert "<NIP>5260250274</NIP>" in xml_str
    assert "<P_2>FV/2026/01</P_2>" in xml_str
    assert "<P_15>2460.00</P_15>" in xml_str  # 2000 * 1.23


def test_fa3_xml_generation():
    supplier = KSeFParty(nip="5260250274", name="Sprzedawca Sp. z o.o.")
    customer = KSeFParty(nip="5252389023", name="Nabywca S.A.")
    item = KSeFInvoiceItem(line_id="1", description="Towar testowy", quantity=1.0, unit_price=500.0, vat_rate=8.0)

    invoice = KSeFInvoice(
        invoice_id="FV/2026/02",
        issue_date="2026-08-13",
        sale_date="2026-08-13",
        supplier=supplier,
        customer=customer,
        items=[item],
        schema_version=KSeFSchemaVersion.FA_3
    )

    xml_str = KSeFInvoiceGenerator.generate_xml(invoice)
    assert "FA (3)" in xml_str
    assert "http://crd.gov.pl/wzor/2025/01/01/13500/" in xml_str


def test_xades_signing():
    raw_xml = "<?xml version=\"1.0\"?><Faktura><Naglowek/></Faktura>"
    signed_xml = XAdESSignerWrapper.sign_xml(raw_xml)

    assert "<ds:Signature" in signed_xml
    assert "<xades:QualifyingProperties" in signed_xml
    assert "</Faktura>" in signed_xml


def test_gateway_full_submission_and_upo_workflow():
    gateway = KSeFEInvoiceGateway(environment=KSeFEnvironment.TEST)
    
    # 1. Authenticate Session
    session = gateway.authenticate("5260250274")
    assert session.is_valid() is True
    assert session.nip == "5260250274"

    # 2. Prepare & Submit Invoice
    supplier = KSeFParty(nip="5260250274", name="MF PL")
    customer = KSeFParty(nip="5252389023", name="Allegro Sales")
    item = KSeFInvoiceItem(line_id="1", description="Usługi chmurowe", quantity=1.0, unit_price=1000.0, vat_rate=23.0)

    invoice = KSeFInvoice(
        invoice_id="FV/2026/100",
        issue_date="2026-08-13",
        sale_date="2026-08-13",
        supplier=supplier,
        customer=customer,
        items=[item]
    )

    ksef_ref = gateway.submit_invoice(invoice)
    assert ksef_ref.startswith("5260250274-")
    assert invoice.status == KSeFInvoiceStatus.ACCEPTED

    # 3. Poll Status
    status_info = gateway.check_status(ksef_ref)
    assert status_info["processing_code"] == 200
    assert status_info["status"] == "ACCEPTED"

    # 4. Download UPO XML Receipt
    upo_xml = gateway.download_upo(status_info["ksef_number"])
    assert "<Potwierdzenie" in upo_xml
    assert "<KodStatusu>200</KodStatusu>" in upo_xml
    assert "Krajowy System e-Faktur" in upo_xml

    # 5. List Invoices
    stored = gateway.list_invoices()
    assert len(stored) >= 1
    assert stored[0].invoice_id == "FV/2026/100"
