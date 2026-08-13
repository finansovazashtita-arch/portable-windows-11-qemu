"""
Unit & Integration Test Suite for Polish GUS BIR API Client (M79).
"""

import pytest
from src.integration.gus_bir_api import GUSBIRClient, GUSCompanyData, KNOWN_GUS_TEST_COMPANIES


def test_gus_bir_login_and_logout():
    client = GUSBIRClient(use_test_env=True)
    sess_id = client.login()

    assert sess_id is not None
    assert sess_id.startswith("GUS-SESS-")
    assert client.session_id == sess_id

    logged_out = client.logout()
    assert logged_out is True
    assert client.session_id is None


def test_gus_search_known_company_by_nip():
    client = GUSBIRClient(use_test_env=True)
    comp = client.search_by_nip("5260250274")

    assert comp.nip == "5260250274"
    assert "MINISTERSTWO FINANSÓW" in comp.name
    assert comp.city == "Warszawa"
    assert comp.active is True
    assert comp.vat_status == "ACTIVE"
    assert "ul. Świętokrzyska 12" in comp.full_address()


def test_gus_search_allegro_by_nip():
    client = GUSBIRClient(use_test_env=True)
    comp = client.search_by_nip("5252389023")

    assert comp.nip == "5252389023"
    assert "ALLEGRO" in comp.name
    assert comp.city == "Poznań"
    assert "47.91.Z" in comp.pkd_codes


def test_gus_search_by_regon():
    client = GUSBIRClient(use_test_env=True)
    comp = client.search_by_regon("140615500")

    assert comp.regon == "140615500"
    assert comp.nip == "5252389023"
    assert "ALLEGRO" in comp.name


def test_gus_search_generated_valid_nip():
    client = GUSBIRClient(use_test_env=True)
    # CD Projekt NIP: 7792400025
    comp = client.search_by_nip("7792400025")

    assert comp.nip == "7792400025"
    assert comp.active is True
    assert comp.city == "Warszawa"


def test_gus_invalid_nip_raises():
    client = GUSBIRClient(use_test_env=True)
    with pytest.raises(ValueError):
        client.search_by_nip("1234567890")
