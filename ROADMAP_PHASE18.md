# Phase 18 Strategic Roadmap: Enterprise Edge AI & Mobile Receipt Scanner Suite

## Vision & Objective
Phase 18 extends the Microinvest Bank Statement OCR & Delta Pro Accounting Automation platform with local WebAssembly / On-Device OCR processing for mobile devices. It enables instant offline scanning of fiscal receipts (фискални бонове) and paper/PDF invoices with automated double-entry accounting entry generation into Microinvest Delta Pro.

---

## Strategic Milestones

### Milestone M67: Enterprise Edge AI & Mobile Receipt Scanner Suite (`m67_edge_ai_mobile_suite`)
- **Objective**: Implement local WebAssembly/On-Device OCR engine for mobile devices to perform instant offline receipt & invoice scanning with automatic accounting entry generation into Delta Pro.
- **Scope**:
  - WebAssembly (WASM) / On-Device OCR engine for Bulgarian fiscal receipts and mobile invoices (`src/ocr/edge_ai_mobile_suite.py`).
  - Mobile camera pre-processing: deskewing, binarization, reflection suppression, and image quality assessment (`EXCELLENT`, `GOOD`, `LOW_LIGHT`, `SKEWED`, `BLURRED`).
  - Bulgarian National Revenue Agency (НАП) Fiscal QR Code parsing & cross-validation format (`BG:EIK*FM*RECEIPT_NO*DATE*TIME*TOTAL`).
  - Automated extraction of seller EIK/Bulstat, Fiscal Memory (ФМ), Fiscal Device (ЗУ), receipt number, payment method (Cash, Card, Voucher, Accountable Person), line items, and VAT breakdown (20%, 9%, 0%).
  - Offline-first encrypted queue management with HMAC-SHA256 tamper protection, local IndexedDB/file storage fallback, and hash-based deduplication (`OfflineReceiptQueueGuard`).
  - Double-entry accounting entry mapping (Debit 601/602/609 + Debit 4531 -> Credit 501/422/401/503) with Cash Desk Manager (РКО) integration.
  - Microinvest Delta Pro TransferData XML (`<TransferData xmlns="urn:Transfer">`) and CSV export generator.
  - Mobile Edge AI REST API endpoints in FinansProtect Web UI Dashboard (`/api/v1/mobile/scan`, `/api/v1/mobile/sync`, `/api/v1/mobile/status`).
- **Target Deliverables**: `src/ocr/edge_ai_mobile_suite.py`, `tests/ocr/test_edge_ai_mobile_suite.py`, `ROADMAP_PHASE18.md`
