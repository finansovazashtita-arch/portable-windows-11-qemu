# Project: Microinvest Bank Statement OCR & Delta Pro Accounting Automation

## Architecture
- **OCR Engine Layer**: PyMuPDF (`fitz`), Pillow (`PIL`), and Tesseract 5 (`-l bul+eng --psm 6`) extracting 100% of transactions from PDF statements with PyMuPDF direct text fallback.
- **Multi-Bank Extraction Architecture**: `src/ocr/multi_bank_extractor.py` supporting auto-detection and specialized parsing for DSK Bank (`STSA`), UniCredit Bulbank (`UNCR`), United Bulgarian Bank / ОББ (`UBBS`), and Postbank / Eurobank Bulgaria (`BPBI`).
- **Automated Email Intake Layer**: `src/intake/email_parser.py` & `src/intake/cloudflare_worker.js` supporting MIME email parsing, IMAP/Gmail polling, Cloudflare Email Routing stream ingestion, and automatic PDF/ZIP attachment extraction (`POST /email-intake`).
- **Multi-PDF Batch Queue Engine**: `src/ocr/batch_processor.py` supporting directory scanning, ZIP archive ingestion, fault-tolerant batch processing, and multi-statement transaction aggregation.
- **OECD SAF-T & NRA Tax Audit Exporter**: `src/audit/saft_exporter.py` producing OECD SAF-T v2.0 XML audit files for Bulgarian National Revenue Agency (НАП) compliance audits.
- **High Availability (HA) Clustering Engine**: `src/cluster/ha_failover.py` & `scripts/deploy_ha_cluster.sh` providing multi-node HA cluster management across `macmini-primary` (`100.83.83.8`) and `macmini-secondary` (`100.70.181.127`) with automatic leader election and failover request routing.
- **Real-Time Cash Flow Forecasting Engine**: `src/ai/cashflow_forecaster.py` projecting 30/60/90-day liquidity trends, moving average cash flow forecasts, and Bulgarian VAT tax liability estimations.
- **AI Fraud Prevention & Anomaly Detection Engine**: `src/ai/fraud_detector.py` providing real-time guardrails for unverified IBAN changes, cross-bank duplicate invoices, monetary amount spikes, and suspicious narrative keywords.
- **VIES VAT & E-Invoicing Sync Layer**: `src/integration/vies_vat_checker.py` validating Bulgarian/EU counterparty VAT registration against European Commission VIES REST API with EN 16931 compliance.
- **Multi-Tenant Isolation & RBAC Security Layer**: `src/security/tenant_rbac.py` enforcing multi-company data isolation, cryptographic JWT token validation, and role-based access control (`ADMIN`, `SENIOR_ACCOUNTANT`, `JUNIOR_ACCOUNTANT`, `AUDITOR`).
- **Automated Nightly Backup Manager**: `src/backup/nightly_backup.py` & `scripts/schedule_nightly_backup.sh` providing scheduled snapshots of MS SQL database (`SQLEXPRESS`), `C:\TRANSFER.LOG` audit logs, Infisical Vault secrets, and 30-day retention pruning.
- **FinansProtect Web UI Audit Dashboard**: `src/dashboard/web_ui/` & `src/dashboard/dashboard_server.py` providing real-time visual monitoring of bank statement intake queues, total processed turnover (€), SHA-256 audit integrity logs, and Windows 11 VM VNC control on port `8095`.
- **Translation & Rules Engine Layer**: Bulgarian double-entry accounting translation engine. Handles account mapping (503, 401, 411, 501, 621, 602, 304, 4531/4532, 702/703), EIK/IBAN checksum validation, SHA-256 deduplication, and Microinvest TransferData XML (`urn:Transfer`) + CSV generation.
- **Unsloth AI Fine-Tuning & Active Learning Layer**: `src/ai/unsloth_classifier.py`, `src/ai/unsloth_finetune.py` & `src/ai/active_learning_loop.py` capturing accountant feedback, accumulating instruction dataset pairs (`data/active_learning_dataset.jsonl`), and triggering incremental Unsloth QLoRA fine-tuning.
- **Production Docker Compose Packaging**: `Dockerfile`, `docker-compose.yml`, and `scripts/deploy_production_stack.sh` providing zero-downtime containerized stack deployment across macmini-primary and secondary nodes.
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
| 12 | E2E Verification & Hardening | Pass 100% of E2E tests (194/194 passed) and complete Tier 5 coverage | M5 | DONE |
| 13 | Self-Hosted Ecosystem Integration | Connect Infisical, n8n, Supabase, Obsidian Vault, Unsloth AI, OpenBalancer Telemetry | M6 | DONE |
| 14 | Multi-PDF Batch Queue & ZIP Processing | Directory scanner, ZIP archive ingestion, fault-tolerant batch execution (`POST /process-batch`) | M7 | DONE |
| 15 | Automated Email Intake Pipeline | IMAP/Gmail fetcher, MIME parser, Cloudflare Email Routing Worker (`POST /email-intake`) | M8 | DONE |
| 16 | Unsloth AI Fine-Tuning Module | QLoRA dataset generator (1,000+ Bulgarian accounting pairs) & FastLanguageModel SFTTrainer config | M9 | DONE |
| 17 | Production Docker Compose Stack | `Dockerfile`, `docker-compose.yml`, health checks, zero-downtime stack deployment | M10 | DONE |
| 18 | Multi-Bank Extractor Engine | Auto-detection and specialized OCR parsing for DSK, UniCredit, UBB, Postbank | M11 | DONE |
| 19 | FinansProtect Web UI Dashboard | Real-time visual monitoring dashboard (`src/dashboard/web_ui/`) on port `8095` | M12 | DONE |
| 20 | Automated Nightly Backup Manager | Daily SQL DB, C:\TRANSFER.LOG, Infisical secrets backups with 30-day retention pruning | M13 | DONE |
| 21 | Active Learning Feedback Loop | Accountant correction capture, instruction dataset accumulation & incremental Unsloth retraining | M14 | DONE |
| 22 | Multi-Tenant Isolation & RBAC | Multi-company statement & DB isolation, JWT authentication, role-based permissions | M15 | DONE |
| 23 | E-Invoicing & VIES VAT Sync | European Commission VIES REST API validation for counterparty BG/EU VAT numbers | M16 | DONE |
| 24 | AI Fraud Prevention Engine | Real-time guardrails for IBAN changes, duplicate invoices, monetary spikes & suspicious keywords | M17 | DONE |
| 25 | High Availability HA Clustering | Multi-node HA cluster management across macmini-primary and secondary with automated failover | M18 | DONE |
| 26 | Cash Flow Forecasting Engine | 30/60/90-day liquidity projections, moving average cash flow forecasts & VAT liability estimations | M19 | DONE |
| 27 | OECD SAF-T & NRA Tax Audit Exporter | OECD SAF-T v2.0 XML compliance audit files for Bulgarian National Revenue Agency (НАП) | M20 | DONE |

## Milestones & Status
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | `m1_ocr_extraction` | PDF rendering, Tesseract OCR parsing, 21 transaction extractions, canonical JSON output | none | DONE |
| M2 | `m2_accounting_translation` | Double-entry translation, account mapping, EIK/IBAN validation, TransferData XML generation | M1 | DONE |
| M3 | `m3_vm_vnc_sql_automation` | Delta Pro Chart of Accounts UI setup, VNC & PowerShell Base64 automated import into SQLEXPRESS | M2 | DONE |
| M4 | `m4_audit_log_export` | 3-way reconciliation (PDF ↔ Journal ↔ SQL DB), persistent C:\TRANSFER.LOG export on Windows 11 VM | M3 | DONE |
| E2E | `m_e2e_testing` | E2E Test infrastructure, Tiers 1-4 test suite creation, publish TEST_READY.md | none | DONE |
| M5 | `m5_final_e2e_verification` | Pass 100% of E2E test suite (194/194 passed) and RAM optimization on QEMU Apple Silicon | M4, E2E | DONE |
| M6 | `m6_full_ecosystem_integration` | Integrate Infisical Vault, Obsidian Vault Sync, Unsloth AI Classifier, Supabase, OpenBalancer | M5 | DONE |
| M7 | `m7_multi_pdf_batch_queue` | Batch processing queue for processing multiple bank PDF statements, ZIP archives, and multi-page statements | M6 | DONE |
| M8 | `m8_automated_email_intake` | IMAP/Gmail/Cloudflare Worker email intake parser to automatically ingest PDF attachments into n8n webhook | M7 | DONE |
| M9 | `m9_unsloth_fine_tuning` | Fine-tune Unsloth.ai Llama-3.2-3B model on 1,000+ Bulgarian bank transaction narratives for 99.9% accuracy | M8 | DONE |
| M10 | `m10_docker_compose_production` | Production `docker-compose.yml` packaging for single-command stack launch across macmini nodes | M9 | DONE |
| M11 | `m11_multi_bank_extractors` | Multi-bank statement OCR extraction engine supporting DSK, UniCredit, UBB, Postbank | M10 | DONE |
| M12 | `m12_finansprotect_web_ui` | FinansProtect Web UI Audit Dashboard (`src/dashboard/web_ui/`) on port `8095` | M11 | DONE |
| M13 | `m13_automated_nightly_backup` | Scheduled MS SQL DB, audit log, and Infisical secrets backups with 30-day retention pruning | M12 | DONE |
| M14 | `m14_active_learning_loop` | Active learning feedback loop for continuous Unsloth LLM fine-tuning based on accountant overrides | M13 | DONE |
| M15 | `m15_multi_tenant_rbac` | Multi-tenant company isolation, JWT authentication, and role-based access control (RBAC) | M14 | DONE |
| M16 | `m16_e_invoicing_vies_sync` | European Commission VIES REST API validation for counterparty BG/EU VAT numbers | M15 | DONE |
| M17 | `m17_fraud_prevention_anomaly_detection` | AI Fraud Prevention & Anomaly Detection engine for IBAN validation, duplicate invoices & monetary spikes | M16 | DONE |
| M18 | `m18_ha_clustering_failover` | High Availability HA Clustering across macmini-primary and secondary with automated failover | M17 | DONE |
| M19 | `m19_cashflow_forecasting` | Real-time cash flow forecasting, 30/60/90-day liquidity projections & VAT tax liability estimation | M18 | DONE |
| M20 | `m20_saft_nra_exporter` | OECD SAF-T v2.0 XML compliance audit files for Bulgarian National Revenue Agency (НАП) | M19 | DONE |

## Code Layout
- `src/audit/`: OECD SAF-T Exporter (`saft_exporter.py`), SQL verification & TRANSFER.LOG exporter (`generate_transfer_log.py`)
- `src/ai/`: Cash Flow Forecaster (`cashflow_forecaster.py`), Fraud Detector (`fraud_detector.py`), Active Learning Loop (`active_learning_loop.py`), Unsloth AI classifier & fine-tuner (`unsloth_classifier.py`, `unsloth_finetune.py`)
- `src/cluster/`: High Availability Cluster Manager (`ha_failover.py`)
- `src/integration/`: VIES VAT Checker (`vies_vat_checker.py`), Obsidian Vault exporter (`obsidian_exporter.py`) & Supabase logger (`supabase_logger.py`)
- `src/security/`: Multi-Tenant RBAC (`tenant_rbac.py`) & Infisical Vault client (`infisical_vault.py`)
- `src/backup/`: Automated Nightly Backup Manager (`nightly_backup.py`)
- `src/dashboard/web_ui/`: FinansProtect Web UI Dashboard static assets (`index.html`, `styles.css`, `app.js`)
- `src/dashboard/`: Dashboard server & OpenBalancer telemetry client (`dashboard_server.py`, `openbalancer_client.py`)
- `src/ocr/`: PDF OCR, multi-bank extractors & batch processing (`extract_dsk_statement.py`, `multi_bank_extractor.py`, `batch_processor.py`)
- `src/intake/`: Automated Email Intake & Cloudflare Email Worker (`email_parser.py`, `cloudflare_worker.js`)
- `src/accounting/`: Bulgarian double-entry translation & XML generator (`translate_to_delta.py`)
- `src/vm_automation/`: VNC & PowerShell Base64 QEMU automation scripts (`import_to_deltapro.py`)
- `scripts/`: Microinvest n8n service, HA cluster deployer, nightly backup scheduler (`microinvest_n8n_service.py`, `deploy_ha_cluster.sh`, `schedule_nightly_backup.sh`, `deploy_production_stack.sh`)
- `tests/`: Unit and E2E test suites (194/194 passed)
