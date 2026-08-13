"""
Unit & Integration Test Suite for KSeF REST API Handlers (M79).
"""

import pytest
from src.integration.ksef_api import (
    get_ksef_health_handler,
    post_ksef_auth_session_handler,
    post_ksef_generate_xml_handler,
    post_ksef_submit_handler,
    get_ksef_status_handler,
    get_ksef_upo_handler,
    post_ksef_gus_check_handler,
    post_ksef_validate_nip_handler,
    get_ksef_invoices_handler
)


def test_api_health_handler():
    res = get_ksef_health_handler()
    assert res["status"] == "UP"
    assert res["gateway"] == "Poland KSeF Gateway M79"
    assert "FA(2)" in res["supported_schemas"]
    assert "FA(3)" in res["supported_schemas"]


def test_api_auth_session_handler():
    body = {
        "nip": "5260250274",
        "token_key": "SECRET_TEST_TOKEN",
        "environment": "TEST"
    }
    res = post_ksef_auth_session_handler(body)
    assert res["success"] is True
    assert res["session_token"].startswith("KSEF-SESS-5260250274")
    assert res["nip"] == "5260250274"


def test_api_validate_nip_handler():
    res_valid = post_ksef_validate_nip_handler({"nip": "5260250274"})
    assert res_valid["is_valid"] is True

    res_invalid = post_ksef_validate_nip_handler({"nip": "1234567890"})
    assert res_invalid["is_valid"] is False


def test_api_generate_xml_handler():
    payload = {
        "invoice_id": "FV/API/001",
        "schema_version": "FA(2)",
        "supplier": {"nip": "5260250274", "name": "MF PL"},
        "customer": {"nip": "5252389023", "name": "Allegro"},
        "items": [{
          "description": "Usługi doradcze",
          "quantity": 1.0,
          "unit_price": 2000.0,
          "vat_rate": 23.0
        }]
    }
    res = post_ksef_generate_xml_handler(payload)
    assert res["success"] is True
    assert res["invoice_id"] == "FV/API/001"
    assert "<?xml version=" in res["xml"]
    assert res["gross_total"] == 2460.0


def test_api_submit_invoice_handler():
    payload = {
        "invoice_id": "FV/API/002",
        "schema_version": "FA(2)",
        "supplier": {"nip": "5260250274", "name": "MF PL"},
        "customer": {"nip": "5252389023", "name": "Allegro"},
        "items": [{
          "description": "Licencja oprogramowania",
          "quantity": 1.0,
          "unit_price": 10000.0,
          "vat_rate": 23.0
        }]
    }
    res = post_ksef_submit_handler(payload)
    assert res["success"] is True
    assert res["status"] == "ACCEPTED"
    assert res["ksef_reference_number"].startswith("5260250274-")

    # Status check handler
    status_res = get_ksef_status_handler(res["ksef_reference_number"])
    assert status_res["status"] == "ACCEPTED"

    # UPO download handler
    upo_res = get_ksef_upo_handler(res["upo_number"])
    assert "<Potwierdzenie" in upo_res["upo_xml"]

    # List handler
    list_res = get_ksef_invoices_handler()
    assert list_res["count"] >= 1


def test_api_gus_check_handler():
    res = post_ksef_gus_check_handler({"nip": "5260250274"})
    assert res["success"] is True
    assert res["company"]["nip"] == "5260250274"
    assert "MINISTERSTWO FINANSÓW" in res["company"]["name"]
