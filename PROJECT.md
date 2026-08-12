# Project: Microinvest Bank Statement OCR & Delta Pro Accounting Automation

## Architecture
- **OCR Engine Layer**: PyMuPDF (`fitz`), Pillow (`PIL`), and Tesseract 5 (`-l bul+eng --psm 6`) extracting 100% of transactions from DSK Bank PDF statements with PyMuPDF direct text fallback.
- **Automated Email Intake Layer**: `src/intake/email_parser.py` & `src/intake/cloudflare_worker.js` supporting MIME email parsing, IMAP/Gmail polling, Cloudflare Email Routing stream ingestion, and automatic PDF/ZIP attachment extraction (`POST /email-intake`).
- **Multi-PDF Batch Queue Engine**: `src/ocr/batch_processor.py` supporting directory scanning, ZIP archive ingestion, fault-tolerant batch processing, and multi-statement transaction aggregation.
- **Translation & Rules Engine Layer**: Bulgarian double-entry accounting translation engine. Handles account mapping (503, 401, 411, 501, 621, 602, 304, 4531/4532, 702/703), EIK/IBAN checksum validation, SHA-256 deduplication, and Microinvest TransferData XML (`urn:Transfer`) + CSV generation.
- **Unsloth AI Narrative Classifier**: `src/ai/unsloth_classifier.py` powered by `unsloth/Llama-3.2-3B-Instruct-bg` rule set for intelligent narrative categorization.
- **Infisical Vault Secrets Manager**: `src/security/infisical_vault.py` integrated with `infisical-standalone` (`http://100.83.83.8:8080`).
- **Obsidian Vault Exporter**: `src/integration/obsidian_exporter.py` syncing Markdown accounting notes into `/Users/diokarabaz/Documents/Obsidian Vault/Microinvest-Accounting/`.
- **Supabase Database Logger**: `src/integration/supabase_logger.py` persisting audit runs to `supabase-db`.
- **OpenBalancer Telemetry Client**: `src/dashboard/openbalancer_client.py` emitting live telemetry to OpenBalancer Dashboard (`https://n8n.openbalancer.com`).
- **Windows 11 QEMU VM Automation Layer**: VNC (`127.0.0.1:5901`) and PowerShell Base64 automation interacting with Microinvest Delta Pro (`C:\Program Files (x86)\Microinvest\Delta Pro\DeltaPro.exe`) and MS SQL Server (`SQLEXPRESS` / `MSSQLSERVER`) inside `windows11_portable.qcow2`.
- **Verification & Audit Layer**: Direct SQL verification (`sqlcmd`) and persistent audit export `C:\TRANSFER.LOG` on Windows 11 VM storage.

## Feature Inventory
| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| 1 | PDF OCR & Image Preprocessing | Render 1.pdf pages to 300 DPI PNG, PyMuPDF fallback, Tesseract bul+eng psm 6 | M1 | DONE |
| 2 | Transaction Line-Item Extraction | Extract date, counterparty, doc number, debit/credit amount, narrative, balance (21 items) | M1 | DONE |
| 3 | Canonical JSON Serialization | Format extracted line items into canonical JSON schema | M1 | DONE |
| 4 | Double-Entry Account Mapping | Map transactions to Bulgarian chart of accounts (503, 401, 411, 501, 621, 602, etc.) | M2 | DONE |
| 5 | Counterparty & Tax Validation | Validate 9/13-digit EIK checksums, IBAN Mod-97, VIES VAT IDs, and SHA-256 dedup keys | M2 | DONE |
| 6 | Microinvest XML & CSV Export | Generate `<TransferData xmlns="urn:Transfer">` double-entry XML and Delta BG CSV files | M2 | DONE |
| 7 | Delta Pro Chart of Accounts Setup | Select Chart of Accounts in Delta Pro GUI via VNC automation | M3 | DONE |
| 8 | Delta Pro Operation Import | Automate entry/import of operations into Microinvest Delta Pro / SQLEXPRESS database | M3 | DONE |
| 9 | Database SQL Verification | Query SQLEXPRESS tables (Partners, Operations, OperationDetails) via sqlcmd | M4 | DONE |
| 10 | Persistent Audit Log Export | Export validated C:\TRANSFER.LOG on persistent Windows 11 QEMU VM storage | M4 | DONE |
| 11 | E2E Test Suite Creation | Create requirement-driven opaque-box E2E test infra (Tiers 1-4) and publish TEST_READY.md | E2E Track | DONE |
| 12 | E2E Verification & Hardening | Pass 100% of E2E tests (157/157 passed) and complete Tier 5 coverage | M5 | DONE |
| 13 | Self-Hosted Ecosystem Integration | Connect Infisical, n8n, Supabase, Obsidian Vault, Unsloth AI, OpenBalancer Telemetry | M6 | DONE |
| 14 | Multi-PDF Batch Queue & ZIP Processing | Directory scanner, ZIP archive ingestion, fault-tolerant batch execution (`POST /process-batch`) | M7 | DONE |
| 15 | Automated Email Intake Pipeline | IMAP/Gmail fetcher, MIME parser, Cloudflare Email Routing Worker (`POST /email-intake`) | M8 | DONE |

## Milestones & Status
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | `m1_ocr_extraction` | PDF rendering, Tesseract OCR parsing, 21 transaction extractions, canonical JSON output | none | DONE |
| M2 | `m2_accounting_translation` | Double-entry translation, account mapping, EIK/IBAN validation, TransferData XML generation | M1 | DONE |
| M3 | `m3_vm_vnc_sql_automation` | Delta Pro Chart of Accounts UI setup, VNC & PowerShell Base64 automated import into SQLEXPRESS | M2 | DONE |
| M4 | `m4_audit_log_export` | 3-way reconciliation (PDF ↔ Journal ↔ SQL DB), persistent C:\TRANSFER.LOG export on Windows 11 VM | M3 | DONE |
| E2E | `m_e2e_testing` | E2E Test infrastructure, Tiers 1-4 test suite creation, publish TEST_READY.md | none | DONE |
| M5 | `m5_final_e2e_verification` | Pass 100% of E2E test suite (157/157 passed) and RAM optimization on QEMU Apple Silicon | M4, E2E | DONE |
| M6 | `m6_full_ecosystem_integration` | Integrate Infisical Vault, Obsidian Vault Sync, Unsloth AI Classifier, Supabase, OpenBalancer | M5 | DONE |
| M7 | `m7_multi_pdf_batch_queue` | Batch processing queue for processing multiple bank PDF statements, ZIP archives, and multi-page statements | M6 | DONE |
| M8 | `m8_automated_email_intake` | IMAP/Gmail/Cloudflare Worker email intake parser to automatically ingest PDF attachments into n8n webhook | M7 | DONE |

## 🎯 Next Priority Roadmap Milestones
| # | Name | Proposed Scope | Target |
|---|------|----------------|--------|
| **M9** | `m9_unsloth_fine_tuning` | Fine-tune Unsloth.ai Llama-3.2-3B model on 10,000+ Bulgarian bank transaction narratives for 99.9% account prediction accuracy | Upcoming |
| **M10**| `m10_docker_compose_production` | Production `docker-compose.yml` packaging for single-command stack launch across macmini-primary and secondary nodes | Upcoming |

## Code Layout
- `src/intake/`: Automated Email Intake & Cloudflare Email Worker (`email_parser.py`, `cloudflare_worker.js`)
- `src/ocr/`: PDF OCR & batch processing scripts (`extract_dsk_statement.py`, `batch_processor.py`)
- `src/accounting/`: Bulgarian double-entry translation & XML generator (`translate_to_delta.py`)
- `src/ai/`: Unsloth AI narrative classifier (`unsloth_classifier.py`)
- `src/security/`: Infisical Vault client (`infisical_vault.py`)
- `src/integration/`: Obsidian Vault exporter & Supabase logger (`obsidian_exporter.py`, `supabase_logger.py`)
- `src/dashboard/`: OpenBalancer telemetry client (`openbalancer_client.py`)
- `src/vm_automation/`: VNC & PowerShell Base64 QEMU automation scripts (`import_to_deltapro.py`)
- `src/audit/`: SQL verification & TRANSFER.LOG exporter (`generate_transfer_log.py`)
- `scripts/`: Microinvest n8n service & workflow deployment scripts (`microinvest_n8n_service.py`, `deploy_n8n_workflow.py`, `test_batch_execution.py`)
- `tests/`: Unit and E2E test suites (157/157 passed)
