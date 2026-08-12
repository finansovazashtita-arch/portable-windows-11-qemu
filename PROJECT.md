# Project: Microinvest Bank Statement OCR & Delta Pro Accounting Automation

## Architecture
- **OCR Engine Layer**: PyMuPDF (`fitz`), Pillow (`PIL`), and Tesseract 5 (`-l bul+eng --psm 6`) extracting 100% of transactions from PDF statements with PyMuPDF direct text fallback.
- **Peppol Cross-Border EU E-Invoicing Engine**: `src/integration/peppol_einvoicing.py` generating, parsing, and validating Peppol BIS Billing v3.0 UBL v2.1 XML invoices meeting European EN 16931 e-invoicing standards.
- **Sovereign Autonomous Enterprise AI Agent Swarm Engine (24/7/365)**: `src/ai/autonomous_agent_swarm.py` coordinating a self-healing swarm of specialized AI cognitive agents (`AuditorAgent`, `ReconcilerAgent`, `FraudGuardAgent`, `ForecasterAgent`) with automatic fault-recovery and 24/7/365 audit loops.
- **Zero-Trust HSM Cryptographic Signer Engine**: `src/security/hsm_signer.py` providing tamper-proof PKCS#11 / YubiKey HSM hardware token cryptographic signatures for `C:\TRANSFER.LOG` audit files and e-invoices.
- **Automated Customs & Excise Tax Accounting**: `src/accounting/customs_excise_accounting.py` generating double-entry journal entries for customs duties (Accounts 304/457), excise taxes (304/458), import VAT (4531/457), and bank settlements (457/503).
- **Multi-Modal Document Reconciliation Engine**: `src/ai/multimodal_reconciler.py` providing 3-way cross-matching between PDF invoices, scanned paper cash receipts (фискални бонове), and bank statement transactions.
- **Continuous Disaster Recovery (DR) Multi-Region Replication**: `src/backup/disaster_recovery_replication.py` & `scripts/run_dr_replication.sh` providing zero-data-loss replication of SQL backups, `C:\TRANSFER.LOG` audit logs, Infisical secrets, and active learning datasets across nodes and off-site cloud storage.
- **Open Banking PSD2 REST API Ingestion**: `src/intake/psd2_openbanking.py` supporting direct real-time transaction streaming and Berlin Group PSD2 API integration for DSK Bank, UniCredit Bulbank, UBB, and Postbank.
- **Automated Payroll & Social Security Integration**: `src/accounting/payroll_accounting.py` generating double-entry journal entries for gross salaries (604/421), employee social security (421/455), income tax / DOD (421/454), net salary payments (421/503), and employer social security (605/455).
- **Autonomous Image Preprocessor**: `src/ocr/image_preprocessor.py` providing adaptive binarization, noise reduction, contrast enhancement, and deskewing for poor quality scanned statements.
- **Multi-Bank Extraction Architecture**: `src/ocr/multi_bank_extractor.py` supporting auto-detection and specialized parsing for DSK Bank (`STSA`), UniCredit Bulbank (`UNCR`), United Bulgarian Bank / ОББ (`UBBS`), and Postbank / Eurobank Bulgaria (`BPBI`).
- **Automated Email Intake Layer**: `src/intake/email_parser.py` & `src/intake/cloudflare_worker.js` supporting MIME email parsing, IMAP/Gmail polling, Cloudflare Email Routing stream ingestion, and automatic PDF/ZIP attachment extraction (`POST /email-intake`).
- **Multi-PDF Batch Queue Engine**: `src/ocr/batch_processor.py` supporting directory scanning, ZIP archive ingestion, fault-tolerant batch processing, and multi-statement transaction aggregation.
- **Mobile Notifications & Telegram Bot Guard**: `src/integration/telegram_notifier.py` dispatching real-time mobile and Telegram alerts for high/critical fraud risk flags, HA cluster failover events, and audit discrepancies.
- **Multi-Currency FX Revaluation Engine**: `src/accounting/fx_revaluation.py` fetching live BNB/ECB exchange rates, handling fixed EUR/BGN peg (1.95583), and generating double-entry FX gain/loss journal entries (Accounts 724 / 624).
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
| 12 | E2E Verification & Hardening | Pass 100% of E2E tests (226/226 passed) and complete Tier 5 coverage | M5 | DONE |
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
| 28 | Multi-Currency FX Revaluation Engine | Live BNB/ECB rates, EUR/BGN fixed peg, and double-entry FX gain/loss entries (724 / 624) | M21 | DONE |
| 29 | Telegram & Mobile Alert Guard | Instant Telegram alerts for high/critical fraud flags, HA failover & audit discrepancies | M22 | DONE |
| 30 | Autonomous Image Preprocessor | Adaptive contrast, sharpness, median noise reduction, and binarization for low-quality scans | M23 | DONE |
| 31 | Automated Payroll Accounting Engine | Double-entry journal entries for gross salaries (604/421), social security (455), and tax (454) | M24 | DONE |
| 32 | Open Banking PSD2 Ingestion Engine | Direct Berlin Group PSD2 API REST streaming for DSK, UniCredit, UBB, and Postbank | M25 | DONE |
| 33 | Continuous DR Multi-Region Replication | Zero-data-loss async snapshot sync across nodes and off-site cloud storage | M26 | DONE |
| 34 | Multi-Modal Document Reconciler | 3-way matching between PDF invoices, paper cash receipts, and bank statements | M27 | DONE |
| 35 | Customs & Excise Tax Accounting Engine | Double-entry journal entries for customs duties (304/457), excise taxes (304/458), and import VAT (4531/457) | M28 | DONE |
| 36 | Zero-Trust HSM Cryptographic Signer | PKCS#11 / YubiKey HSM hardware token cryptographic signatures for audit logs and e-invoices | M29 | DONE |
| 37 | Autonomous AI Agent Swarm Engine | 24/7/365 self-healing swarm of cognitive AI agents auditing, reconciling, and forecasting | M30 | DONE |
| 38 | Peppol EU E-Invoicing Integration | Peppol BIS Billing v3.0 UBL v2.1 XML generation and EN 16931 compliance validation | M31 | DONE |

## Milestones & Status
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | `m1_ocr_extraction` | PDF rendering, Tesseract OCR parsing, 21 transaction extractions, canonical JSON output | none | DONE |
| M2 | `m2_accounting_translation` | Double-entry translation, account mapping, EIK/IBAN validation, TransferData XML generation | M1 | DONE |
| M3 | `m3_vm_vnc_sql_automation` | Delta Pro Chart of Accounts UI setup, VNC & PowerShell Base64 automated import into SQLEXPRESS | M2 | DONE |
| M4 | `m4_audit_log_export` | 3-way reconciliation (PDF ↔ Journal ↔ SQL DB), persistent C:\TRANSFER.LOG export on Windows 11 VM | M3 | DONE |
| E2E | `m_e2e_testing` | E2E Test infrastructure, Tiers 1-4 test suite creation, publish TEST_READY.md | none | DONE |
| M5 | `m5_final_e2e_verification` | Pass 100% of E2E test suite (226/226 passed) and RAM optimization on QEMU Apple Silicon | M4, E2E | DONE |
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
| M21 | `m21_multi_currency_fx_revaluation` | Live BNB/ECB rates, EUR/BGN fixed peg, and double-entry FX gain/loss entries (724 / 624) | M20 | DONE |
| M22 | `m22_telegram_mobile_bot_guard` | Real-time mobile & Telegram alerts for high/critical fraud flags, HA failover & audit discrepancies | M21 | DONE |
| M23 | `m23_image_preprocessor` | Adaptive contrast, sharpness, median noise reduction, and binarization for low-quality scans | M22 | DONE |
| M24 | `m24_payroll_accounting` | Automated double-entry payroll accounting entries for salaries (604/421), tax (454) & security (455) | M23 | DONE |
| M25 | `m25_psd2_openbanking` | Direct Berlin Group PSD2 API REST streaming for DSK, UniCredit, UBB, and Postbank | M24 | DONE |
| M26 | `m26_disaster_recovery_replication` | Zero-data-loss async snapshot sync across nodes and off-site cloud storage | M25 | DONE |
| M27 | `m27_multimodal_reconciler` | 3-way matching between PDF invoices, paper cash receipts, and bank statements | M26 | DONE |
| M28 | `m28_customs_excise_accounting` | Automated double-entry journal entries for customs duties (304/457), excise taxes (304/458) & import VAT | M27 | DONE |
| M29 | `m29_hsm_audit_signer` | PKCS#11 / YubiKey HSM hardware token cryptographic signatures for audit logs and e-invoices | M28 | DONE |
| M30 | `m30_autonomous_agent_swarm` | 24/7/365 self-healing swarm of cognitive AI agents auditing, reconciling, and forecasting | M29 | DONE |
| M31 | `m31_peppol_einvoicing` | Peppol BIS Billing v3.0 UBL v2.1 XML generation and EN 16931 compliance validation | M30 | DONE |

## Code Layout
- `src/integration/`: Peppol EU E-Invoicing Engine (`peppol_einvoicing.py`), Telegram Bot Guard (`telegram_notifier.py`), VIES VAT Checker (`vies_vat_checker.py`), Obsidian Vault exporter (`obsidian_exporter.py`) & Supabase logger (`supabase_logger.py`)
- `src/ai/`: Autonomous Agent Swarm (`autonomous_agent_swarm.py`), Multi-Modal Document Reconciler (`multimodal_reconciler.py`), Cash Flow Forecaster (`cashflow_forecaster.py`), Fraud Detector (`fraud_detector.py`), Active Learning Loop (`active_learning_loop.py`), Unsloth AI classifier & fine-tuner (`unsloth_classifier.py`, `unsloth_finetune.py`)
- `src/security/`: Zero-Trust HSM Cryptographic Signer (`hsm_signer.py`), Multi-Tenant RBAC (`tenant_rbac.py`) & Infisical Vault client (`infisical_vault.py`)
- `src/accounting/`: Customs & Excise Accounting Engine (`customs_excise_accounting.py`), Payroll Accounting Engine (`payroll_accounting.py`), FX Revaluation Engine (`fx_revaluation.py`), Bulgarian double-entry translation & XML generator (`translate_to_delta.py`)
- `src/backup/`: DR Multi-Region Replication Manager (`disaster_recovery_replication.py`), Automated Nightly Backup Manager (`nightly_backup.py`)
- `src/intake/`: Open Banking PSD2 client (`psd2_openbanking.py`), Automated Email Intake & Cloudflare Email Worker (`email_parser.py`, `cloudflare_worker.js`)
- `src/ocr/`: Image Preprocessor (`image_preprocessor.py`), PDF OCR, multi-bank extractors & batch processing (`extract_dsk_statement.py`, `multi_bank_extractor.py`, `batch_processor.py`)
- `src/audit/`: OECD SAF-T Exporter (`saft_exporter.py`), SQL verification & TRANSFER.LOG exporter (`generate_transfer_log.py`)
- `src/cluster/`: High Availability Cluster Manager (`ha_failover.py`)
- `src/dashboard/web_ui/`: FinansProtect Web UI Dashboard static assets (`index.html`, `styles.css`, `app.js`)
- `src/dashboard/`: Dashboard server & OpenBalancer telemetry client (`dashboard_server.py`, `openbalancer_client.py`)
- `src/vm_automation/`: VNC & PowerShell Base64 QEMU automation scripts (`import_to_deltapro.py`)
- `scripts/`: Microinvest n8n service, DR replication runner, HA cluster deployer, nightly backup scheduler (`microinvest_n8n_service.py`, `run_dr_replication.sh`, `deploy_ha_cluster.sh`, `schedule_nightly_backup.sh`, `deploy_production_stack.sh`)
- `tests/`: Unit and E2E test suites (226/226 passed)
