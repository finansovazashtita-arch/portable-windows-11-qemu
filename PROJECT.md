# Project: Microinvest Bank Statement OCR & Delta Pro Accounting Automation

## Architecture
- **OCR Engine Layer**: PyMuPDF (`fitz`), Pillow (`PIL`), and Tesseract 5 (`-l bul+eng --psm 6`) extracting 100% of transactions from `/Volumes/KINGSTON/Persist/Scans/Storgozia AD/DSK_01-06/1.pdf`.
- **Translation & Rules Engine Layer**: Bulgarian double-entry accounting translation engine leveraging `/Users/diokarabaz/hermes-work/fintect-a11y-20260629231256/MICROINVEST-OCR` rulesets. Handles account mapping (503, 401, 411, 501, 621, 602, 304, 4531/4532, 702/703), EIK/IBAN checksum validation, SHA-256 deduplication, and Microinvest TransferData XML (`urn:Transfer`) + CSV generation.
- **Windows 11 QEMU VM Automation Layer**: VNC (`127.0.0.1:5901`) and PowerShell Base64 automation interacting with Microinvest Delta Pro (`C:\Program Files (x86)\Microinvest\Delta Pro\DeltaPro.exe`) and MS SQL Server (`SQLEXPRESS` / `MSSQLSERVER`) inside `windows11_portable.qcow2`.
- **Verification & Audit Layer**: Direct SQL verification (`sqlcmd`) and persistent audit export `C:\TRANSFER.LOG` on Windows 11 VM storage.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | PDF OCR & Image Preprocessing | Render 1.pdf pages to 300 DPI PNG, repair tesseract bul.traineddata, run tesseract bul+eng psm 6 | M1 | survey_ocr_explorer_1 |
| 2 | Transaction Line-Item Extraction | Extract posting date, value date, counterparty name/IBAN, doc number, debit/credit amount, narrative, currency, balance (21 line items) | M1 | survey_ocr_explorer_1 |
| 3 | Canonical JSON Serialization | Format extracted line items into canonical JSON schema | M1 | survey_ocr_explorer_1 |
| 4 | Double-Entry Account Mapping | Map transactions to Bulgarian chart of accounts (503, 401, 411, 501, 621, 602, 304, 4531/4532, 702/703) | M2 | survey_accounting_miner_1 |
| 5 | Counterparty & Tax Validation | Validate 9/13-digit EIK checksums, IBAN Mod-97, VIES VAT IDs, and SHA-256 dedup keys | M2 | survey_accounting_miner_1 |
| 6 | Microinvest XML & CSV Export | Generate `<TransferData xmlns="urn:Transfer">` double-entry XML and Delta BG CSV files | M2 | survey_accounting_miner_1 |
| 7 | Delta Pro Chart of Accounts Setup | Select Chart of Accounts in Delta Pro GUI via VNC automation to prevent modal error | M3 | survey_vnc_qemu_explorer_1 |
| 8 | Delta Pro Operation Import | Automate entry/import of operations into Microinvest Delta Pro / SQLEXPRESS database via VNC/PowerShell | M3 | survey_vnc_qemu_explorer_1 |
| 9 | Database SQL Verification | Query SQLEXPRESS tables (Partners, Operations, OperationDetails) via sqlcmd to verify line-item reconciliation | M4 | survey_vnc_qemu_explorer_1 |
| 10 | Persistent Audit Log Export | Export validated C:\TRANSFER.LOG on persistent Windows 11 QEMU VM storage | M4 | survey_vnc_qemu_explorer_1 |
| 11 | E2E Test Suite Creation | Create requirement-driven opaque-box E2E test infra (Tiers 1-4) and publish TEST_READY.md | E2E Track | dual_track_policy |
| 12 | E2E Verification & Hardening | Pass 100% of E2E tests and perform Tier 5 adversarial coverage hardening | M5 | dual_track_policy |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | `m1_ocr_extraction` | PDF page rendering, Tesseract OCR parsing, 21 transaction extractions, canonical JSON output | none | DONE (bfb97406-93e6-4059-a051-04a563675827) |
| M2 | `m2_accounting_translation` | Double-entry translation, account mapping (503/401/411/621/etc.), EIK/IBAN validation, TransferData XML generation | M1 | DONE (351befff-d780-4ca4-9953-cb7793f90beb) |
| M3 | `m3_vm_vnc_sql_automation` | Delta Pro Chart of Accounts UI setup, VNC & PowerShell Base64 automated import into Delta Pro / SQLEXPRESS | M2 | DONE (93f8a2b5-5e3a-4214-8092-1e8ce946bf2e) |
| M4 | `m4_audit_log_export` | 3-way reconciliation (PDF ↔ Journal ↔ SQL DB), persistent C:\TRANSFER.LOG export on Windows 11 VM | M3 | DONE |
| E2E | `m_e2e_testing` | E2E Test infrastructure, Tiers 1-4 test suite creation, publish TEST_READY.md | none | DONE (0d60fc3c-c222-4bab-9490-76c2f755ff26) |
| M5 | `m5_final_e2e_verification` | Pass 100% of E2E test suite (Tiers 1-4) and complete Tier 5 adversarial coverage hardening | M4, E2E | IN_PROGRESS |

## Interface Contracts
### OCR Extractor (M1) ↔ Translation Engine (M2)
- Input: `/Volumes/KINGSTON/Persist/Scans/Storgozia AD/DSK_01-06/1.pdf`
- Output: `data/extracted_transactions.json`
- Schema:
  ```json
  {
    "statement_metadata": {
      "account_holder": "СТОРГОЗИЯ АД",
      "eik": "114077876",
      "iban": "BG71STSA93000028013479",
      "currency": "EUR",
      "period_start": "01.01.2026",
      "period_end": "31.01.2026",
      "opening_balance": 5883.29
    },
    "transactions": [
      {
        "item_id": 1,
        "posting_date": "YYYY-MM-DD",
        "value_date": "YYYY-MM-DD",
        "counterparty_name": "string",
        "counterparty_iban": "string",
        "document_number": "string",
        "debit_amount": 0.00,
        "credit_amount": 0.00,
        "narrative_description": "string",
        "currency": "EUR",
        "balance": 0.00
      }
    ]
  }
  ```

### Translation Engine (M2) ↔ VM Import Automation (M3)
- Input: `data/extracted_transactions.json`
- Output: `data/microinvest_transferdata.xml`, `data/journal_entries.json`
- XML Format: `<TransferData xmlns="urn:Transfer">` conforming to Microinvest Delta Pro import specification.

### VM Import Automation (M3) ↔ Audit Export (M4)
- Input: `data/microinvest_transferdata.xml`
- Output: SQLEXPRESS DB records inside Windows 11 VM (`windows11_portable.qcow2`).

### Audit Export (M4) ↔ Final E2E Verification (M5)
- Input: SQLEXPRESS DB query results, `data/journal_entries.json`, `1.pdf`
- Output: Persistent `C:\TRANSFER.LOG` inside Windows 11 QEMU VM.

## Code Layout
- `src/ocr/`: PDF OCR extraction scripts (`extract_dsk_statement.py`)
- `src/accounting/`: Bulgarian double-entry translation & XML generator (`translate_to_delta.py`)
- `src/vm_automation/`: VNC & PowerShell Base64 QEMU automation scripts (`import_to_deltapro.py`)
- `src/audit/`: SQL verification & TRANSFER.LOG exporter (`generate_transfer_log.py`)
- `tests/e2e/`: E2E test harness and test suite (`test_e2e_pipeline.py`)
