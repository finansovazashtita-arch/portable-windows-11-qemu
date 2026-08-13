# Phase 24 Strategic Roadmap: Predictive AI Advisory & Autonomous Decision Engine

## Vision & Objective
Phase 24 introduces an enterprise-grade **Predictive AI Advisory Engine** (`src/ai/predictive_advisor.py`), REST API router (`src/ai/advisory_api.py`), and interactive executive web dashboard (`src/dashboard/web_ui/advisory.html`) to FinansProtect. This milestone synthesizes ledger balances, liquidity forecasts, working capital metrics, Bulgarian tax laws (CITA/VATA), and solvency indicators into proactive C-level prescriptive recommendations, multi-scenario simulations, double-entry journal advice, and multi-format executive brief exports (PDF, JSON, CSV).

---

## Strategic Milestones

### Milestone M77: Predictive AI Advisory (`m77_predictive_ai_advisory`)
- **Objective**: Deliver a full-stack Predictive AI Advisory platform featuring multi-scenario financial trajectory simulations, prescriptive C-level recommendation cards with expected BGN yield, Bulgarian double-entry accounting advice, Cash Conversion Cycle (CCC) optimization, statutory tax strategy advisor (CITA 10%, VATA 100k threshold, 5% dividend tax timing), and an interactive web UI dashboard (`src/dashboard/web_ui/advisory.html`).
- **Scope**:
  - **Predictive AI Advisory Engine (`src/ai/predictive_advisor.py`)**: Multi-scenario trajectory forecasting (Base Case, Optimistic, Downturn, Expansion), Altman Z-Score solvency distress prediction, working capital CCC optimization (DSO, DPO, DIO), and tax strategy pre-calculation under Art. 92 & 194 CITA / Art. 96 VATA.
  - **Prescriptive Recommendation Generator**: Actionable advisory cards with expected BGN financial impact, confidence score, urgency level (CRITICAL, HIGH, MEDIUM, LOW), category, and step-by-step action plan.
  - **Bulgarian Double-Entry Journal Advisor**: Recommended journal entries (Accounts 401, 411, 503, 604, 609, 421, 454, 241, 101, 498, 504, 709) with statutory references.
  - **Advisory REST API Gateway (`src/ai/advisory_api.py`)**: Endpoints (`/api/v1/advisory/insights`, `/api/v1/advisory/scenarios`, `/api/v1/advisory/cash-conversion-cycle`, `/api/v1/advisory/tax-strategy`, `/api/v1/advisory/export`) integrated into `dashboard_server.py` and documented in `openapi_docs.py`.
  - **Interactive Web UI Advisory Dashboard (`src/dashboard/web_ui/advisory.html`)**: Responsive executive workspace featuring What-If scenario sliders, interactive SVG trajectory charts, filterable prescriptive insight cards, CCC metric dials, and multi-format export buttons.
- **Dependencies**: M12, M19, M41, M64, M76
- **Target Deliverables**: `src/ai/predictive_advisor.py`, `src/ai/advisory_api.py`, `src/dashboard/web_ui/advisory.html`, `tests/ai/test_predictive_advisor.py`, `tests/ai/test_advisory_api.py`, `tests/dashboard/test_advisory_dashboard.py`
- **Status**: Completed

---

## Verification Criteria
- M77: 100% test coverage across `tests/ai/test_predictive_advisor.py`, `tests/ai/test_advisory_api.py`, and `tests/dashboard/test_advisory_dashboard.py`; REST API endpoints respond with valid advisory payloads; Web UI dashboard loads and renders interactive SVG trajectory graphs; export handler generates valid JSON, CSV, and PDF summary outputs.
