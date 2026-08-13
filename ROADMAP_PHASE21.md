# Phase 21 Roadmap: M71 AI-Powered Smart Invoice Matching & Auto-Reconciliation

## Milestone Overview
**M71: AI-Powered Smart Invoice Matching & Auto-Reconciliation Engine** extends the core financial reconciliation capabilities of the platform by using AI similarity scoring, character n-gram narrative embeddings, transliteration normalization, and fuzzy amount tolerance matching to automatically pair issued/received invoices with bank statement transactions.

## Problem Solved
Module M27 provides hard-rule 3-way matching (exact match by BGN amount and EIK). However, in real-world accounting, payment narratives are often incomplete or contain discrepancies such as:
- Missing invoice prefixes or leading zeros (e.g. `INV-000102` vs `плащане фактура 102`).
- Transliteration between Cyrillic and Latin counterparty names (e.g. `Tekstil BG EOOD` ↔ `Текстил БГ ЕООД`).
- Rounding differences, bank wire transfer fees (±0.50 to ±5.00 BGN), or prompt-payment cash discounts (skonto 1-2%).

M71 solves this by producing multi-factor confidence scores (0.0 to 1.0 / 0% to 100%) and providing an interactive **1-Click Auto-Suggest UI** for accountants.

---

## Core Capabilities Implemented

### 1. Semantic Narrative Matching via Vector Embeddings (`NarrativeEmbeddingEngine`)
- **Character N-Gram Cosine Similarity**: Computes TF-IDF character 3-gram embedding vectors for Bulgarian and English payment narrative text.
- **Invoice Number Extraction & Normalization**: Regular expression token extraction with leading-zero stripping and sub-string matching.
- **Cyrillic <-> Latin Transliteration**: Automatic transliteration mapping for Bulgarian counterparty names and notes.
- **OCR Misread Fault Tolerance**: Tolerates misread characters (e.g. `0` vs `O`, `1` vs `l`).

### 2. Fuzzy Amount Matching (`FuzzyAmountMatcher`)
- **Exact match**: 1.0 score (0.00 BGN difference).
- **Rounding variance**: 0.98 score (<= 0.05 BGN difference).
- **Bank fee tolerance**: Scaled score between 0.80 and 0.95 for differences up to `abs_tolerance` (e.g. 5.00 BGN).
- **Cash discount tolerance**: Scaled score between 0.75 and 0.90 for percentage differences up to `percent_tolerance` (e.g. 2.0%).
- **Multi-currency Support**: Automatic conversion using EUR/BGN fixed peg (1.95583).

### 3. Multi-Factor AI Confidence Scoring (`SmartInvoiceMatcher`)
- Multi-weighted scoring formula:
  $$\text{Confidence} = w_{\text{nar}} \cdot S_{\text{narrative}} + w_{\text{amt}} \cdot S_{\text{amount}} + w_{\text{party}} \cdot S_{\text{party}}$$
- Tiers: `HIGH` (>=85%), `MEDIUM` (65%-84%), `LOW` (40%-64%), `UNMATCHED` (<40%).
- Automatically proposes standard double-entry journal entries (e.g. `Дб 503 / Кр 411` or `Дб 401 / Кр 503`).

### 4. Auto-Suggest UI & REST API Integration (`FinansProtect Dashboard`)
- **Web UI Panel**: Live **AI Auto-Suggest Card / Table** on port `8095` displaying candidate pairs, confidence badges (`98.5% High`), difference details, and 1-Click **"Потвърди" (Confirm)** / **"Отхвърли" (Reject)** buttons.
- **REST Endpoints**:
  - `GET /api/v1/reconciliation/pending-matches`
  - `POST /api/v1/reconciliation/smart-match`
  - `POST /api/v1/reconciliation/confirm`
  - `POST /api/v1/reconciliation/reject`
- **OpenAPI 3.1 Spec**: Updated in `src/api/openapi_docs.py` with Swagger UI interactive documentation at `/api/docs`.

### 5. Audit Ledger & Active Learning Loop Persistence
- Confirmation updates the tamper-evident SHA-256 audit hash chain (`AuditLedgerGuard`).
- Confirmed match feedback is enqueued into `data/active_learning_dataset.jsonl` for fine-tuning `Unsloth` AI models.

---

## Verification Results
- **Unit Test Suite**: `tests/ai/test_smart_invoice_matcher.py` (7/7 passed).
- **API Test Suite**: `tests/dashboard/test_smart_reconciliation_api.py` (4/4 passed).
- **Full Project Test Suite**: 100% passed with zero regressions.
