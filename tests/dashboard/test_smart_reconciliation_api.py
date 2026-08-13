"""
API Integration tests for M71 Smart Invoice Reconciliation REST & OpenAPI endpoints.
"""

import json
import pytest
from src.dashboard.dashboard_server import DashboardHandler, COMPLIANCE_ENGINE


def test_smart_reconciliation_pending_matches_api(monkeypatch):
    payload = COMPLIANCE_ENGINE.get_telemetry_payload()
    matches = payload.get("smart_reconciliation_pending", [])
    assert isinstance(matches, list)
    assert len(matches) >= 2

    match_item = matches[0]
    assert "invoice_number" in match_item
    assert "overall_confidence_pct" in match_item
    assert "suggested_journal_entry" in match_item


def test_smart_reconciliation_confirm_api():
    payload = COMPLIANCE_ENGINE.get_telemetry_payload()
    matches = payload.get("smart_reconciliation_pending", [])
    assert len(matches) > 0

    target_id = matches[0]["match_id"]
    res = COMPLIANCE_ENGINE.confirm_smart_match(target_id, confirmed_by="test_accountant")

    assert res["success"] is True
    assert res["status"] == "ACCOUNTANT_CONFIRMED"
    assert res["confirmed_by"] == "test_accountant"
    assert "journal_entry" in res
    assert "audit_hash" in res


def test_smart_reconciliation_reject_api():
    payload = COMPLIANCE_ENGINE.get_telemetry_payload()
    matches = payload.get("smart_reconciliation_pending", [])
    assert len(matches) > 0

    target_id = matches[0]["match_id"]
    res = COMPLIANCE_ENGINE.reject_smart_match(target_id)

    assert res["success"] is True
    assert res["status"] == "REJECTED"


def test_smart_reconciliation_batch_api():
    invoices = [
        {
            "invoice_id": "INV-BATCH-01",
            "doc_number": "10055",
            "amount": 950.00,
            "counterparty_name": "Софтуер БГ ЕООД",
        }
    ]
    bank_txs = [
        {
            "item_id": "TX-BATCH-01",
            "credit_amount": 950.00,
            "narrative": "плащане фактура 10055 Софтуер",
        }
    ]

    res = COMPLIANCE_ENGINE.submit_smart_match_batch(invoices, bank_txs)
    assert res["success"] is True
    assert res["candidates_count"] >= 1
    c = res["candidates"][0]
    assert c["invoice_number"] == "10055"
    assert c["overall_confidence_pct"] >= 85.0
