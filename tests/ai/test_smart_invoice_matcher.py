"""
Unit & Integration Tests for M71: AI-Powered Smart Invoice Matching & Auto-Reconciliation Engine.
"""

import pytest
from src.ai.smart_invoice_matcher import (
    SmartInvoiceMatcher,
    SmartReconciliationCandidate,
    MatchConfidenceTier,
    ReconcileMatchStatus,
    NarrativeEmbeddingEngine,
    FuzzyAmountMatcher,
    CounterpartyMatcher,
    transliterate_cyrillic_to_latin,
    normalize_text_token,
    extract_numeric_tokens,
)
from src.ai.multimodal_reconciler import MultiModalReconciler, ReconciliationStatus
from src.dashboard.realtime_compliance_ui import RealTimeComplianceEngine


def test_transliteration_and_normalization():
    cyr = "Текстил БГ ЕООД фактура №102"
    lat = transliterate_cyrillic_to_latin(cyr)
    assert "Tekstil" in lat or "Tekstil" in normalize_text_token(cyr)

    norm = normalize_text_token("Фактура №00000102 / 2026г.")
    assert "102" in norm

    nums = extract_numeric_tokens("плащане фактура 000102")
    assert "102" in nums
    assert "000102" in nums


def test_narrative_embedding_engine():
    # 1. Cosine Similarity between Bulgarian narratives
    text1 = "Плащане по фактура 102 за доставка на текстил"
    text2 = "плащ ф-ра 102 текстил бг"
    sim = NarrativeEmbeddingEngine.compute_cosine_similarity(text1, text2)
    assert sim > 0.40

    # 2. Invoice Number Matching
    inv_no = "INV-000102"
    bank_nar = "плащане фактура 102 Текстил ЕООД"
    score, exact_match = NarrativeEmbeddingEngine.compute_invoice_number_similarity(inv_no, bank_nar)
    assert exact_match is True
    assert score >= 0.95

    # Combined score
    total_score, matched = NarrativeEmbeddingEngine.score_narrative_matching(inv_no, text1, bank_nar)
    assert matched is True
    assert total_score >= 0.85


def test_fuzzy_amount_matcher():
    # 1. Exact match
    score, diff = FuzzyAmountMatcher.score_amount_similarity(100.0, 100.0)
    assert score == 1.0
    assert diff == 0.0

    # 2. Rounding tolerance (0.04 BGN)
    score, diff = FuzzyAmountMatcher.score_amount_similarity(100.04, 100.0)
    assert score == 0.98
    assert abs(diff - 0.04) < 0.001

    # 3. Bank transfer fee tolerance (1.50 BGN)
    score, diff = FuzzyAmountMatcher.score_amount_similarity(1000.0, 998.50, abs_tolerance=5.0)
    assert score >= 0.85
    assert abs(diff - 1.50) < 0.001

    # 4. Cash discount / skonto percentage tolerance (1.5%)
    score, diff = FuzzyAmountMatcher.score_amount_similarity(1000.0, 985.0, percent_tolerance=2.0)
    assert score >= 0.75

    # 5. Currency conversion (850 EUR to BGN peg)
    score_eur, diff_eur = FuzzyAmountMatcher.score_amount_similarity(850.0, 1662.46, inv_curr="EUR", bank_curr="BGN")
    assert score_eur >= 0.95
    assert diff_eur < 0.10


def test_counterparty_matcher():
    # 1. EIK match
    score_eik = CounterpartyMatcher.score_counterparty_match("831201948", "Текстил ООД", "831201948", "Tekstil OOD")
    assert score_eik == 1.0

    # 2. Name fuzzy match
    score_name = CounterpartyMatcher.score_counterparty_match(None, "Евротранс Логистик ООД", None, "Eurotrans Logistic OOD")
    assert score_name >= 0.60


def test_smart_invoice_matcher_end_to_end():
    invoices = [
        {
            "invoice_id": "INV-01",
            "doc_number": "0000000102",
            "amount": 1250.00,
            "currency": "BGN",
            "counterparty_name": "Текстил БГ ЕООД",
            "counterparty_eik": "831201948",
            "description": "Текстилни материали",
        }
    ]

    bank_txs = [
        {
            "item_id": "TX-01",
            "credit_amount": 1248.50, # 1.50 BGN bank fee difference
            "currency": "BGN",
            "narrative": "плащане фактура 102 Текстил",
            "counterparty_name": "Tekstil BG EOOD",
            "counterparty_eik": "831201948",
        }
    ]

    candidates = SmartInvoiceMatcher.match_invoices_and_bank_txs(invoices, bank_txs)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.invoice_id == "INV-01"
    assert cand.bank_tx_id == "TX-01"
    assert cand.overall_confidence >= 0.85
    assert cand.confidence_tier in (MatchConfidenceTier.HIGH, MatchConfidenceTier.MEDIUM)
    assert cand.invoice_number_exact_match is True

    # Test confirmation
    res = SmartInvoiceMatcher.confirm_reconciliation_match(cand, confirmed_by="senior_accountant")
    assert res["success"] is True
    assert res["status"] == "ACCOUNTANT_CONFIRMED"
    assert res["confirmed_by"] == "senior_accountant"
    assert "suggested_journal_entry" in cand.to_dict()


def test_multimodal_reconciler_m71_fallback():
    invoices = [
        {"doc_number": "0000000102", "amount": 1250.00}
    ]
    # Bank tx amount has small rounding difference 1248.50 BGN (exact match fails)
    bank_txs = [
        {
            "item_id": "TX-M71-99",
            "credit_amount": 1248.50,
            "narrative": "плащане фактура 102 Текстил",
        }
    ]

    matches = MultiModalReconciler.reconcile_3way(invoices, [], bank_txs)
    assert len(matches) == 1
    match = matches[0]
    assert match.status == ReconciliationStatus.MATCHED
    assert match.bank_tx_id == "TX-M71-99"
    assert "M71 AI" in match.notes


def test_realtime_compliance_engine_smart_reconciliation():
    engine = RealTimeComplianceEngine()
    
    # 1. Verify pending queue was seeded
    initial_pending = engine.get_telemetry_payload().get("smart_reconciliation_pending", [])
    initial_len = len(initial_pending)
    assert initial_len >= 2

    # 2. Confirm a match
    match_to_confirm = initial_pending[0]["match_id"]
    conf_res = engine.confirm_smart_match(match_to_confirm, confirmed_by="chief_auditor")
    assert conf_res["success"] is True
    assert conf_res["status"] == "ACCOUNTANT_CONFIRMED"
    assert conf_res["audit_hash"] != ""

    # Verify pending queue decreased by 1
    updated_pending = engine.get_telemetry_payload().get("smart_reconciliation_pending", [])
    assert len(updated_pending) == initial_len - 1

    # 3. Reject a match
    match_to_reject = updated_pending[0]["match_id"]
    rej_res = engine.reject_smart_match(match_to_reject)
    assert rej_res["success"] is True

    # 4. Batch custom run
    batch_res = engine.submit_smart_match_batch(
        [{"invoice_id": "INV-NEW-99", "doc_number": "99", "amount": 500.00, "counterparty_name": "Софтуер АД"}],
        [{"item_id": "TX-NEW-99", "credit_amount": 500.00, "narrative": "ф-ра 99 софтуер"}]
    )
    assert batch_res["success"] is True
    assert batch_res["candidates_count"] >= 1
