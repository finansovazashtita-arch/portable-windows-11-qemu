# Phase 20 Strategic Roadmap: Bulgarian Business Statutory & Regulatory Compliance Reporting Engine

## Vision & Objective
Phase 20 expands the Microinvest Bank Statement OCR & Delta Pro Accounting Automation platform with statutory enterprise compliance reporting capabilities for Bulgarian legal entities under the Accounting Act (Закон за счетоводството - ЗСч), National Accounting Standards (НСФО), International Financial Reporting Standards (ИФРС / IFRS), Corporate Income Tax Act (ЗКПО / CITA), and Commercial Register (Търговски регистър към Агенция по вписванията).

---

## Strategic Milestones

### Milestone M72: ГФО Generator (🟡 Бизнес — Годишен Финансов Отчет) (`m72_gfo_generator`)
- **Objective**: Deliver an autonomous Bulgarian Annual Financial Statement (ГФО - Годишен Финансов Отчет) generation, reconciliation, statutory validation, and multi-format export engine meeting all Bulgarian legal and regulatory standards.
- **Scope**:
  - Dynamic Trial Balance (Оборотна ведомост - Accounts 100-799) aggregation and financial statement mapping engine (`src/accounting/gfo_generator.py`).
  - Automated statutory Balance Sheet (Счетоводен баланс) generation with Assets (Non-current, Current) vs Liabilities & Equity (Equity, Non-current, Current) balancing (`Assets == Equity + Liabilities`).
  - Automated Income Statement (Отчет за приходите и разходите - ОПР) computation with revenue (Accounts 701-724), operating expense breakdown (Accounts 601-624), accounting profit/loss, 10% corporate income tax, and net profit calculation.
  - Statement of Cash Flows (Отчет за паричните потоци - ОПП) generation (Operating, Investing, Financing activities) with continuous cash balance reconciliation matching Accounts 501 + 503.
  - Statement of Changes in Equity (Отчет за собствения капитал - ОСК) tracking share capital, reserves, retained earnings, and current period result.
  - Explanatory Notes & Accounting Policies (Приложение) compilation including legal entity metadata, EIK/Bulstat, accounting standards (NAS/IFRS), and depreciation policies.
  - Statutory Validation & Audit Engine evaluating balance equation integrity, cross-statement consistency, missing legal disclosures, and zero-activity entity status under Art. 38(9) Accounting Act.
  - Multi-Format Regulatory Serialization:
    - Commercial Register Statutory XML export (`<GFOReport xmlns="urn:bg:registryagency:gfo:v1">`).
    - NSI / NRA Canonical JSON export for enterprise webhooks.
    - Printable statutory HTML/CSS report view for management and auditor signature.
    - Art. 38(9) Accounting Act Declaration of No Activity (Декларация за предприятие с неактивност) export.
  - Audit Ledger Integrity & Cryptographic Hash Registration: Tamper-evident SHA-256 hash chaining of generated GFO documents registered in `C:\TRANSFER.LOG` audit vault.
  - FinansProtect Web UI Dashboard REST API integration (`/api/v1/gfo/generate`, `/api/v1/gfo/validate`, `/api/v1/gfo/export/xml`, `/api/v1/gfo/export/html`, `/api/v1/gfo/no-activity-declaration`).
- **Dependencies**: M51, M56, M65
- **Target Deliverables**: `src/accounting/gfo_generator.py`, `tests/accounting/test_gfo_generator.py`, `ROADMAP_PHASE20.md`
- **Status**: Completed 100%
