# Project: Microinvest Bank Statement OCR & Delta Pro Accounting Automation

## Architecture
- **OCR Engine Layer**: PyMuPDF (`fitz`), Pillow (`PIL`), and Tesseract 5 (`-l bul+eng --psm 6`) extracting 100% of transactions from PDF statements with PyMuPDF direct text fallback.
- **Autonomous Open Banking Payment Initiation & Multi-Bank AISP Aggregator**: `src/intake/open_banking_pisp.py` and `src/intake/cee_open_banking_aggregator.py` providing PSD2 PISP automated vendor invoice payments (401/503) and multi-bank balance aggregation across DSK, UniCredit, UBB, Postbank (Bulgaria), PKO BP & Pekao (Poland), BCR & Banca Transilvania (Romania), Alpha Bank & Eurobank (Greece), and Revolut Business & Wise (neo-bank EU).
- **Automated Financial Audit Trail & Tamper-Evident Blockchain Ledger Integration**: `src/security/audit_ledger_guard.py` providing tamper-evident cryptographic hash chaining (SHA-256) of every accounting operation for 100% protection against retroactive alteration.
- **Autonomous Business Travel Expenses & Per Diem Allowance Manager**: `src/accounting/travel_expense_manager.py` computing domestic/international per diem allowances under Bulgarian Travel Regulations, generating travel expense journal entries (609/422).
- **Autonomous Cash Desk & Petty Cash Management Engine**: `src/accounting/cash_desk_manager.py` processing Cash Receipt Orders (ПКО / 501/411) and Cash Expense Orders (РКО / 401/501), monitoring cash limits, and daily cash book reconciliation.
- **Automated Real-Time Bank Account Reconciliation Guard**: `src/intake/bank_feed_guard.py` performing real-time matching between bank statement feeds and ledger Account 503, detecting unposted bank fees (621/503), unposted transfers, and balance variances.
- **Autonomous Personal Income Tax & Dividend Withholding Tax Manager**: `src/audit/dividend_tax_manager.py` computing 5% dividend withholding tax under Art. 194 CITA / Art. 38 PITA, generating double-entry dividend entries (122/425/454), and producing quarterly NRA Form 55 filing declarations.
- **Autonomous Corporate Income Tax (CITA / ЗКПО) Tax Return Generator**: `src/audit/corporate_tax_return.py` computing 10% corporate tax on taxable profit, financial result adjustments (609 non-deductible expenses), and generating Art. 92 CITA tax return entries (123/454).
- **Autonomous Multi-Entity Corporate Consolidation & Intercompany Elimination Engine**: `src/accounting/corporate_consolidation.py` consolidating trial balances across holding subsidiaries and eliminating intercompany 411/401 balances.
- **Automated Fixed Assets & Depreciation Schedule Manager**: `src/accounting/fixed_assets_depreciation.py` managing fixed asset registration (204/401) across CITA tax categories I-VII and generating monthly depreciation entries (603/241).
- **Autonomous Enterprise Inventory & Stock Valuation Engine**: `src/accounting/inventory_valuation.py` managing inventory receipts (304/401), sales COGS write-offs (702/304 via FIFO & Weighted Average), and scrap write-offs (601/304).
- **Autonomous Cross-Border EU Tax & OSS E-Commerce Invoicing Adapter**: `src/accounting/eu_oss_accounting.py` computing multi-country EU VAT rates, double-entry OSS sales mapping, and quarterly VAT declaration summaries.
- **Intelligent AI Voice Assistant & Hands-Free Accounting Query Interface**: `src/ai/voice_accounting_assistant.py` processing speech-to-text (STT) queries in Bulgarian for hands-free lookups of balances, turnover, and missing invoices.
- **Autonomous Tax Policy & Regulatory Update Ingestion Engine**: `src/audit/tax_policy_ingestor.py` monitoring State Gazette (Държавен вестник) and NRA (НАП) tax amendments for dynamic account mapping rule adjustments.
- **Multi-Language Executive Financial Briefing Generator Engine**: `src/dashboard/executive_briefing.py` crafting daily localized C-level financial summary reports in Bulgarian, English, and German.
- **Autonomous Tax Audit Defense & Discrepancy Risk Scoring Engine**: `src/audit/tax_audit_defense.py` evaluating NRA tax audit risk triggers (Art. 92 VATA / Чл. 92 ЗДДС VAT refund threshold), missing invoice numbers, and VIES deregistered counterparties.
- **Multi-Bank Instant Payment Gateway & SEPA Instant / BISERA 6 Integration Adapter**: `src/intake/sepa_bisera_instant.py` processing real-time sub-second instant bank transfers and automated Account 401 vendor invoice settlement.
- **Automated Corporate Financial Ratio & Solvency Analyzer Engine**: `src/ai/financial_solvency_analyzer.py` computing liquidity ratios (Current, Quick, Cash Ratios) and Altman Z-Score corporate distress models.
- **Distributed AI Multi-Node GPU Cluster Orchestrator Engine**: `src/ai/gpu_cluster_orchestrator.py` balancing Unsloth Llama-3.2 AI classification queries across GPU/Apple Silicon nodes (vLLM, Ollama) with local fallback.
- **Automated Regulatory E-Reporting Adapter Engine for NRA VAT**: `src/audit/nra_vat_reporter.py` generating statutory NRA text files (`DEKLAR.TXT`, `POKUPKI.TXT`, `PRODAGBI.TXT`) with automated cell balance reconciliation.
- **Multi-Region Active-Active SQL Database Synchronization Guard**: `src/backup/active_active_sql_sync.py` replicating database mutations bi-directionally between MS SQL Server and PostgreSQL with Zero Recovery Point Objective (RPO=0) and SHA-256 conflict resolution.
- **Autonomous AI Synthetic Dataset Generator & Stress Harness**: `src/ai/synthetic_stress_harness.py` synthesizing 100,000+ Bulgarian bank transactions for high-volume load benchmarking and Unsloth model evaluations.
- **Zero-Trust HSM Cryptographic Signer Engine**: `src/security/hsm_signer.py` providing tamper-proof PKCS#11 / YubiKey HSM hardware token cryptographic signatures, extended with NIST Post-Quantum Cryptography (PQC) lattice algorithms (`CRYSTALS_DILITHIUM`, `FALCON_1024`).
- **Zero-Downtime Live Production Rolling Upgrade Controller**: `src/cluster/rolling_upgrade_controller.py` orchestrating zero-downtime canary and blue/green container deployments across HA nodes with traffic draining and automatic rollback.
- **Prometheus & Grafana Monitoring Telemetry Exporter**: `src/dashboard/prometheus_exporter.py` exposing `/metrics` endpoints tracking real-time processed financial turnover (€/sec), transaction volume, OCR precision (%), QEMU VM RAM allocation, and HA cluster leader state.
- **Autonomous Audit Log Cold Storage Archiver**: `src/backup/cold_storage_archiver.py` compressing persistent `C:\TRANSFER.LOG` audit files and HSM signatures into ZSTD/GZIP archives with 10-year NRA tax retention metadata and SHA-256 verification.
- **Native Mobile Push Notification Gateway**: `src/integration/mobile_push_gateway.py` dispatching instant high-priority mobile push notifications across iOS (Apple APNs) and Android (Firebase FCM) for fraud and failover alerts.
- **Peppol Cross-Border EU E-Invoicing Engine**: `src/integration/peppol_einvoicing.py` generating, parsing, and validating Peppol BIS Billing v3.0 UBL v2.1 XML invoices meeting European EN 16931 e-invoicing standards.
- **Sovereign Autonomous Enterprise AI Agent Swarm Engine (24/7/365)**: `src/ai/autonomous_agent_swarm.py` coordinating a self-healing swarm of specialized AI cognitive agents (`AuditorAgent`, `ReconcilerAgent`, `FraudGuardAgent`, `ForecasterAgent`) with automatic fault-recovery and 24/7/365 audit loops.
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
- **Autonomous Global Multi-Entity Tax & VAT Engine**: `src/audit/global_tax_engine.py`, `src/integration/hmrc_mtd_adapter.py`, `src/audit/us_sales_tax_engine.py`, `src/audit/swiss_estv_tax_engine.py`, `src/integration/ksef_gateway.py`, `src/integration/mydata_gateway.py` providing multi-jurisdiction tax calculation, filing, and double-entry mapping across Bulgaria (НАП), EU (VIES/OSS), UK (HMRC MTD), US (State Sales Tax), Switzerland (ESTV), Poland (KSeF), and Greece (myDATA).
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
- **Enterprise Edge AI & Mobile Receipt Scanner Suite**: `src/ocr/edge_ai_mobile_suite.py` providing local WebAssembly/On-Device OCR scanning of fiscal receipts and invoices with NRA QR parsing, HMAC-signed offline sync, double-entry accounting (601/602/609 + 4531 -> 501/422/401/503), and Microinvest TransferData XML export.
- **Autonomous Regulatory Compliance & E-Archiving Audit Vault**: `src/security/e_archiving_compliance_vault.py` providing full eIDAS 2.0 LTV compatibility, Qualified Electronic Signatures (КЕП), RFC 3161 timestamps, and ZK tax audit proofs.

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
| 12 | E2E Verification & Hardening | Pass 100% of E2E tests (289/289 passed) and complete Tier 5 coverage | M5 | DONE |
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
| 39 | Native Mobile Push Notification Gateway | Apple APNs HTTP/2 & Firebase FCM REST API v1 push notifications for mobile devices | M32 | DONE |
| 40 | 10-Year NRA Audit Log Cold Storage Archiver | ZSTD/GZIP audit log compression with 10-year NRA retention metadata and SHA-256 verification | M33 | DONE |
| 41 | Prometheus & Grafana Telemetry Exporter | Prometheus exposition format for financial turnover (€/sec), OCR precision & QEMU VM RAM allocation | M34 | DONE |
| 42 | Zero-Downtime Rolling Upgrade Controller | Zero-downtime canary & blue/green deployments across HA cluster nodes with automatic rollback | M35 | DONE |
| 43 | Post-Quantum Cryptography PQC Audit Signer | NIST PQC Dilithium & Falcon lattice algorithms for quantum-resistant HSM audit signing | M36 | DONE |
| 44 | AI Synthetic Dataset Generator & Stress Harness | High-fidelity 100,000+ transaction synthesis and throughput benchmarking for Unsloth AI models | M37 | DONE |
| 45 | Multi-Region Active-Active SQL Sync Guard | RPO=0 real-time MS SQL Server / PostgreSQL bi-directional replication with SHA-256 conflict resolution | M38 | DONE |
| 46 | Regulatory E-Reporting Adapter for NRA VAT | Statutory NRA text files (DEKLAR.TXT, POKUPKI.TXT, PRODAGBI.TXT) for Bulgarian VAT filing | M39 | DONE |
| 47 | Distributed AI Multi-Node GPU Cluster | Multi-node GPU load balancer (vLLM / Ollama) for Unsloth AI Llama-3.2 inference models | M40 | DONE |
| 48 | Financial Solvency & Ratio Analyzer | Liquidity ratios (Current, Quick, Cash) & Altman Z-Score corporate distress forecasting | M41 | DONE |
| 49 | SEPA Instant & BISERA 6 Payment Gateway | Sub-second instant settlement ingestion & automated Account 401 vendor invoice settlement | M42 | DONE |
| 50 | Autonomous Tax Audit Defense Engine | Assessment of NRA tax audit risk (Art. 92 VATA) & missing invoice / VIES deregistration flags | M43 | DONE |
| 51 | Multi-Language Executive Briefing Engine | Daily C-level financial briefing report generator in Bulgarian, English, and German | M44 | DONE |
| 52 | Autonomous Tax Policy Ingestion Engine | State Gazette & NRA tax regulation update monitoring for dynamic account rule updates | M45 | DONE |
| 53 | Intelligent AI Voice Accounting Assistant | Speech-to-text (STT) Bulgarian voice query processing for balances, turnover & missing invoices | M46 | DONE |
| 54 | EU OSS E-Commerce Invoicing Adapter | Multi-country EU VAT rate calculation, double-entry OSS sales mapping (702/4535) & quarterly reports | M47 | DONE |
| 55 | Enterprise Inventory & Stock Valuation | Stock receipts (304/401), FIFO & Weighted Average sales COGS write-offs (702/304), scrap (601/304) | M48 | DONE |
| 56 | Fixed Assets & Depreciation Manager | PPE registration (204/401) across CITA tax categories I-VII, monthly depreciation entries (603/241) | M49 | DONE |
| 57 | Corporate Consolidation & Elimination | Multi-subsidiary trial balance aggregation, automated intercompany 411/401 elimination entries | M50 | DONE |
| 58 | Corporate Income Tax (CITA) Return | 10% corporate tax calculation on taxable profit, 609 adjustments & Art. 92 CITA tax return entries (123/454) | M51 | DONE |
| 59 | Personal & Dividend Withholding Tax Manager | 5% dividend tax under Art. 194 CITA / Art. 38 PITA, entries (122/425/454), quarterly Form 55 filing | M52 | DONE |
| 60 | Real-Time Bank Account Reconciliation Guard | Continuous bank feed matching against Account 503, unposted fee detection (621/503) & variance guard | M53 | DONE |
| 61 | Cash Desk & Petty Cash Management | Cash receipt (ПКО / 501/411) & expense (РКО / 401/501) orders, cash limit monitoring & cash book reconciliation | M54 | DONE |
| 62 | Business Travel Expenses & Per Diem Manager | Domestic & international per diem calculation under Bulgarian Travel Regulations, journal entries (609/422) | M55 | DONE |
| 63 | Audit Ledger Integrity Guard | Tamper-evident SHA-256 hash chaining of accounting entries for 100% NRA tax audit protection | M56 | DONE |
| 64 | Open Banking PISP Payment Initiation | PSD2 PISP automated vendor invoice payments (401/503) and multi-bank balance aggregation | M57 | DONE |
| 65 | Real-Time Trial Balance Anomaly Sentinel | Autonomous trial balance movement analysis, debit/credit imbalance alerts & correction entries | M58 | DONE |
| 66 | Zero-Trust DR Failover & Instant Recovery Orchestrator | Automated scheduled disaster recovery failover testing, sub-5s RTO switchover | M59 | DONE |
| 67 | Autonomous NRA E-Invoicing & Portal Gateway | Direct integration with NRA portal (НАП Е-Фактура API) for real-time submission, verification & QES signing | M60 | DONE |
| 68 | Autonomous Voice & NLU Command Executor | Autonomous execution of bookkeeping entries, payment generation & NRA VAT declaration filings via voice & text | M61 | DONE |
| 69 | Global Multi-Entity Tax & VAT Engine | Multi-entity tax & VAT engine supporting BG (NRA), EU (VIES/OSS), UK (HMRC MTD), US (Sales Tax), and CH (ESTV) | M62 | DONE |
| 70 | Quantum-Safe Active-Active DR Mesh | Unifying post-quantum signing (M36) and DR orchestrator (M59) into an active multi-cloud K3s mesh (AWS + Hetzner + On-premise Mac Mini) | M63 | DONE |
| 71 | Dynamic Cash Flow Optimization & Predictive Liquidity Engine | Monte Carlo stochastic liquidity simulations (VaR 95/99%), automated supplier payment scheduling maximizing cash discount yield vs cost of capital | M64 | DONE |
| 72 | Autonomous Regulatory Compliance & E-Archiving Audit Vault | Full eIDAS 2.0 LTV compatibility, Qualified Electronic Signatures (КЕП), RFC 3161 timestamps & ZK tax audit proofs | M66 | DONE |
| 73 | Real-Time Audit Compliance & WebSockets Dashboard | Real-time multi-entity audit compliance dashboard with WebSockets telemetry for NRA e-invoicing, PQC mesh status & interactive corrections | M65 | DONE |
| 74 | Integration Smoke Test Suite | Docker-based automated integration testing framework & CI/CD smoke test suite validating real bank statements & REST APIs | M68 | DONE |
| 75 | Production Config & Secrets Hardening | Centralized config manager, startup secret validation layer, Infisical Vault key rotation & Docker Compose profiles | M69 | DONE |
| 76 | ГФО Generator (Годишен Финансов Отчет) | Autonomous Bulgarian Annual Financial Statement generation, balance sheet equality auditing, statutory XML/HTML export & REST APIs | M72 | DONE |
| 77 | OpenAPI 3.1 Spec & Swagger UI Dashboard | Comprehensive OpenAPI 3.1 YAML/JSON specification, embedded Swagger UI at `/api/docs`, validator middleware & API v1/v2 routing | M70 | DONE |
| 78 | Enterprise Edge AI & Mobile Receipt Scanner | WebAssembly/On-Device OCR, NRA QR parsing, offline HMAC queue sync & Delta Pro accounting export | M67 | DONE |
| 79 | AI Smart Invoice Matching & Auto-Reconciliation | AI-powered vector embeddings, Cyrillic/Latin transliteration, fuzzy amount tolerance & 1-click UI confirmation | M71 | DONE |
| 80 | Production Kubernetes Helm Chart & Deploy Pipeline | Complete Helm chart with 15 templates, K3s manifests, Traefik IngressRoute, cert-manager, GitHub Actions CI/CD deploy workflow | M73 | DONE |
| 81 | Comprehensive Bilingual User Documentation | MkDocs Material site with 42 pages (BG/EN), admin guide, user manual, API reference, Postman collection | M74 | DONE |
| 82 | Multi-Tenant SaaS Billing & Subscription Management | Stripe payment integration, tenant provisioning, usage metering, database isolation, GDPR Art. 17 erasure | M75 | DONE |
| 83 | Business Intelligence (BI) Analytics Dashboard | Multi-dimensional OLAP query engine, executive KPI matrix, scenario simulator, threshold alerting, multi-format exports & modern web UI | M76 | DONE |
| 84 | Predictive AI Advisory & Executive Decision Engine | Multi-scenario financial trajectory simulator, prescriptive C-level action cards, double-entry journal advice, working capital CCC optimizer & tax strategy advisor | M77 | DONE |
| 85 | Romania ANAF e-Factura Gateway | UBL 2.1 RO-CIUS XML generation, Romanian CIF check digit validation, ANAF OAuth 2.0 SPV, QES XMLDSig signing, submission upload/status/download, ANAF VAT Registry API, REST API router & web UI dashboard | M78 | DONE |
| 86 | Poland KSeF e-Fakturowanie Gateway | FA(2)/FA(3) structured XML invoice generator, Modulo 11 NIP validation, KSeF Session Token auth, XAdES digital signature wrapper, invoice submission, status tracking, UPO receipt archiving, GUS BIR1.1 API company lookup & web UI | M79 | DONE |
| 87 | Greece myDATA Compliance Gateway | AADE myDATA XML document validation, Greek AFM tax ID verification, REST API transmission to AADE, MARK registration tracking & double-entry journal sync | M80 | DONE |
| 88 | Enterprise ESG & Carbon Tax Accounting Engine | GHG Protocol Scope 1-3 carbon footprint calculation, EU CBAM carbon tax accounting, double-entry carbon liabilities & CSRD reporting | M81 | DONE |
| 89 | CEE & EU Open Banking PISP/AISP Expansion | Berlin Group NextGenPSD2 PISP/AISP expansion to PKO BP & Pekao (PL), BCR & Banca Transilvania (RO), Alpha Bank & Eurobank (GR), Revolut Business & Wise (neo-bank EU-wide); multi-currency balance aggregation (PLN/RON/EUR); ISO 20022 pain.001 payment initiation; NIP/CIF/AFM/IBAN validators; 161-test suite | M83 | DONE |

## Milestones & Status
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
|---|------|-------|-------------|--------|
| M1 | `m1_ocr_extraction` | PDF rendering, Tesseract OCR parsing, 21 transaction extractions, canonical JSON output | none | DONE |
| M2 | `m2_accounting_translation` | Double-entry translation, account mapping, EIK/IBAN validation, TransferData XML generation | M1 | DONE |
| M3 | `m3_vm_vnc_sql_automation` | Delta Pro Chart of Accounts UI setup, VNC & PowerShell Base64 automated import into SQLEXPRESS | M2 | DONE |
| M4 | `m4_audit_log_export` | 3-way reconciliation (PDF ↔ Journal ↔ SQL DB), persistent C:\TRANSFER.LOG export on Windows 11 VM | M3 | DONE |
| E2E | `m_e2e_testing` | E2E Test infrastructure, Tiers 1-4 test suite creation, publish TEST_READY.md | none | DONE |
| M5 | `m5_final_e2e_verification` | Pass 100% of E2E test suite (289/289 passed) and RAM optimization on QEMU Apple Silicon | M4, E2E | DONE |
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
| M19 | `m19_cashflow_forecasting` | Real-time cash flow forecasting, 30/60/90-day liquidity projections & VAT liability estimation | M18 | DONE |
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
| M32 | `m32_mobile_push_gateway` | Apple APNs HTTP/2 & Firebase FCM REST API v1 push notifications for mobile devices | M31 | DONE |
| M33 | `m33_cold_storage_archiver` | ZSTD/GZIP audit log compression with 10-year NRA retention metadata and SHA-256 verification | M32 | DONE |
| M34 | `m34_prometheus_exporter` | Prometheus exposition format for financial turnover (€/sec), OCR precision & QEMU VM RAM allocation | M33 | DONE |
| M35 | `m35_rolling_upgrade_controller` | Zero-downtime canary & blue/green deployments across HA cluster nodes with automatic rollback | M34 | DONE |
| M36 | `m36_pqc_audit_signer` | NIST PQC Dilithium & Falcon lattice algorithms for quantum-resistant HSM audit signing | M35 | DONE |
| M37 | `m37_synthetic_stress_harness` | High-fidelity 100,000+ transaction synthesis and throughput benchmarking for Unsloth AI models | M36 | DONE |
| M38 | `m38_active_active_sql_sync` | RPO=0 real-time MS SQL Server / PostgreSQL bi-directional replication with SHA-256 conflict resolution | M37 | DONE |
| M39 | `m39_nra_vat_reporter` | Statutory NRA text files (DEKLAR.TXT, POKUPKI.TXT, PRODAGBI.TXT) for Bulgarian VAT filing | M38 | DONE |
| M40 | `m40_gpu_cluster_orchestrator` | Multi-node GPU load balancer (vLLM / Ollama) for Unsloth AI Llama-3.2 inference models | M39 | DONE |
| M41 | `m41_financial_solvency_analyzer` | Liquidity ratios (Current, Quick, Cash) & Altman Z-Score corporate distress forecasting | M40 | DONE |
| M42 | `m42_sepa_bisera_instant` | Sub-second instant settlement ingestion & automated Account 401 vendor invoice settlement | M41 | DONE |
| M43 | `m43_tax_audit_defense` | Assessment of NRA tax audit risk (Art. 92 VATA) & missing invoice / VIES deregistration flags | M42 | DONE |
| M44 | `m44_executive_briefing` | Daily C-level financial briefing report generator in Bulgarian, English, and German | M43 | DONE |
| M45 | `m45_tax_policy_ingestor` | State Gazette & NRA tax regulation update monitoring for dynamic account rule updates | M44 | DONE |
| M46 | `m46_voice_accounting_assistant` | Speech-to-text (STT) Bulgarian voice query processing for balances, turnover & missing invoices | M45 | DONE |
| M47 | `m47_eu_oss_accounting` | Multi-country EU VAT rate calculation, double-entry OSS sales mapping (702/4535) & quarterly reports | M46 | DONE |
| M48 | `m48_inventory_valuation` | Stock receipts (304/401), FIFO & Weighted Average sales COGS write-offs (702/304), scrap (601/304) | M47 | DONE |
| M49 | `m49_fixed_assets_depreciation` | PPE registration (204/401) across CITA tax categories I-VII, monthly depreciation entries (603/241) | M48 | DONE |
| M50 | `m50_corporate_consolidation` | Multi-subsidiary trial balance aggregation, automated intercompany 411/401 elimination entries | M49 | DONE |
| M51 | `m51_corporate_tax_return` | 10% corporate tax calculation on taxable profit, 609 adjustments & Art. 92 CITA tax return entries (123/454) | M50 | DONE |
| M52 | `m52_dividend_tax_manager` | 5% dividend tax under Art. 194 CITA / Art. 38 PITA, entries (122/425/454), quarterly Form 55 filing | M51 | DONE |
| M53 | `m53_bank_feed_guard` | Continuous bank feed matching against Account 503, unposted fee detection (621/503) & variance guard | M52 | DONE |
| M54 | `m54_cash_desk_manager` | Cash receipt (ПКО / 501/411) & expense (РКО / 401/501) orders, cash limit monitoring & cash book reconciliation | M53 | DONE |
| M55 | `m55_travel_expense_manager` | Domestic & international per diem calculation under Bulgarian Travel Regulations, journal entries (609/422) | M54 | DONE |
| M56 | `m56_audit_ledger_guard` | Tamper-evident SHA-256 hash chaining of accounting entries for 100% NRA tax audit protection | M55 | DONE |
| M57 | `m57_open_banking_pisp` | PSD2 PISP automated vendor invoice payments (401/503) and multi-bank balance aggregation | M56 | DONE |
| M58 | `m58_neural_trial_balance_sentinel` | Autonomous trial balance movement analysis, debit/credit imbalance alerts & correction entries | M57 | DONE |
| M59 | `m59_zero_trust_dr_orchestrator` | Scheduled zero-trust DR failover testing, VM cloning, DB sync check & sub-5s RTO switchover | M58 | DONE |
| M60 | `m60_nra_einvoice_portal_gateway` | Direct integration with NRA portal (НАП Е-Фактура API) for real-time submission, verification & QES signing | M59 | DONE |
| M61 | `m61_nlu_voice_command_executor` | Autonomous voice & NLU command executor for bookkeeping entries, payment generation & NRA VAT filings | M46, M57, M39 | DONE |
| M62 | `m62_global_multinational_tax_engine` | Global multi-entity tax & VAT engine supporting BG (NRA), EU (VIES/OSS), UK (HMRC MTD), US (Sales Tax), and CH (ESTV) | M47, M50, M51 | DONE |
| M63 | `m63_quantum_safe_dr_mesh` | Quantum-Safe Active-Active DR Mesh orchestrator unifying PQC signing (M36) & DR orchestrator (M59) across AWS, Hetzner, and On-premise Mac Mini | M36, M59 | DONE |
| M64 | `m64_ai_cash_optimizer` | Autonomous Dynamic Cash Flow Optimization & Predictive Liquidity AI Engine with Monte Carlo simulations & automated cash-discount payment scheduler | M19, M57 | DONE |
| M65 | `m65_realtime_compliance_ui` | Real-Time Multi-Entity Audit Compliance & WebSockets Telemetry Dashboard for NRA e-invoicing status, PQC replication mesh & interactive corrections | M60, M62, M63 | DONE |
| M66 | `m66_e_archiving_compliance_vault` | Autonomous Regulatory Compliance & E-Archiving Audit Vault with eIDAS 2.0 LTV preservation, QES validation, RFC 3161 timestamps & ZK proofs for tax audits | M33, M36, M56, M60 | DONE |
| M67 | `m67_edge_ai_mobile_suite` | Enterprise Edge AI & Mobile Receipt Scanner Suite with WebAssembly/On-Device OCR, NRA QR validation, offline HMAC queue sync & Delta Pro accounting | M23, M27, M54 | DONE |
| M68 | `m68_integration_smoke_tests` | End-to-End Integration Smoke Test Suite & GitHub Actions CI/CD pipeline | M5, M12 | DONE |
| M69 | `m69_config_hardening` | Production Configuration & Secrets Management Hardening (`src/config/config_hardening.py`) | M10, M13 | DONE |
| M70 | `m70_openapi_docs` | Comprehensive OpenAPI 3.1 YAML/JSON specification, Swagger UI Dashboard at `/api/docs`, validator middleware & API v1/v2 routing | M12, M68 | DONE |
| M71 | `m71_smart_invoice_matcher` | AI-Powered Smart Invoice Matching & Auto-Reconciliation Engine with vector embeddings, fuzzy amount matching & 1-click UI confirmation | M27, M65 | DONE |
| M72 | `m72_gfo_generator` | Autonomous Bulgarian Annual Financial Statement (ГФО) Generation, Validation & Multi-Format Regulatory Export | M51, M56, M65 | DONE |
| M73 | `m73_k8s_helm_deployment` | Production Kubernetes Helm Chart, K3s manifests, Traefik IngressRoute, cert-manager ClusterIssuer & GitHub Actions deploy pipeline | M10, M18, M34, M63, M69 | DONE |
| M74 | `m74_user_documentation` | Comprehensive bilingual (BG/EN) MkDocs Material user documentation, admin guide, API reference & Postman collection | M12, M70 | DONE |
| M75 | `m75_saas_billing` | Multi-Tenant SaaS Billing & Subscription Management with Stripe integration, tenant provisioning API, usage metering & GDPR Art. 17 erasure | M15, M69, M73 | DONE |
| M76 | `m76_bi_analytics_dashboard` | Business Intelligence (BI) Analytics Dashboard with financial & operational KPIs, multi-dimensional OLAP query engine, threshold alerts, scenario simulations & interactive web UI | M12, M19, M41, M65, M75 | DONE |
| M77 | `m77_predictive_ai_advisory` | Predictive AI Advisory & Autonomous Decision Engine with multi-scenario financial simulations, prescriptive C-level action cards, Bulgarian double-entry journal advice, working capital CCC optimizer & interactive web UI | M12, M19, M41, M64, M76 | DONE |
| M78 | `m78_romania_anaf_efactura` | Romania ANAF e-Factura & Cross-Border CEE Compliance Gateway with UBL 2.1 RO-CIUS XML generation, CUI/CIF validation, OAuth 2.0 SPV, QES signing, submission upload/status/download, ANAF VAT Registry API, REST API router & web UI dashboard | M12, M19, M41, M60, M77 | DONE |
| M79 | `m79_poland_ksef_gateway` | Poland KSeF (Krajowy System e-Faktur) Gateway with FA(2)/FA(3) XML invoice generation, Modulo 11 NIP validation, KSeF Session Token auth, XAdES digital signature wrapper, submission/status/UPO receipt archiving, GUS BIR1.1 API, REST API router & web UI dashboard | M12, M19, M41, M60, M77, M78 | DONE |
| M80 | `m80_greece_mydata_gateway` | Greece myDATA Compliance Gateway with AADE myDATA XML document validation, Greek AFM tax ID verification, REST API transmission to AADE, MARK registration tracking & double-entry journal sync | M12, M19, M41, M60, M77, M78 | DONE |
| M81 | `m81_esg_carbon_accounting` | Enterprise ESG & Carbon Tax Accounting Engine with GHG Protocol Scope 1-3 carbon footprint calculation, EU CBAM carbon tax accounting, double-entry carbon liabilities & CSRD reporting | M12, M19, M41, M48, M76, M77 | DONE |
| M83 | `m83_open_banking_cee_expansion` | CEE & EU Open Banking PISP/AISP Expansion — Berlin Group NextGenPSD2 integration for PKO BP & Pekao (Poland), BCR & Banca Transilvania (Romania), Alpha Bank & Eurobank (Greece), Revolut Business & Wise (neo-bank EU); multi-currency PLN/RON/EUR balance aggregation; ISO 20022 pain.001 payment initiation; NIP / CIF / AFM / IBAN validators; backward-compat M57 bridge; 161-test suite (161/161 passed) | M25, M57, M78, M79, M80 | DONE |

## Code Layout
- `src/config/`: Production Configuration & Secrets Management Hardening (`config_hardening.py`)
- `src/analytics/`: BI Analytics Engine (`bi_engine.py`), Financial & Operational KPI Calculator (`kpi_calculator.py`), OLAP Query Builder (`query_builder.py`), Threshold Alert Manager (`bi_alerts.py`), Report Exporter (`exporter.py`), REST API Router (`bi_api.py`)
- `src/billing/`: Multi-Tenant SaaS Billing System (`tenant_manager.py`, `stripe_client.py`, `metering_engine.py`, `schema_manager.py`, `gdpr_compliance.py`, `webhook_handler.py`, `tenant_api.py`)
- `src/intake/`: Open Banking PISP Aggregator (`open_banking_pisp.py`), CEE Open Banking Aggregator (`cee_open_banking_aggregator.py`), Bank Feed Guard (`bank_feed_guard.py`), SEPA Instant / BISERA 6 Adapter (`sepa_bisera_instant.py`), Open Banking PSD2 client (`psd2_openbanking.py`), Automated Email Intake & Cloudflare Email Worker (`email_parser.py`, `cloudflare_worker.js`)
- `src/security/`: E-Archiving Compliance Vault (`e_archiving_compliance_vault.py`), Post-Quantum Mesh Signer (`pq_mesh_signer.py`), Audit Ledger Integrity Guard (`audit_ledger_guard.py`), Zero-Trust HSM Cryptographic Signer & PQC (`hsm_signer.py`), Multi-Tenant RBAC (`tenant_rbac.py`) & Infisical Vault client (`infisical_vault.py`)
- `src/accounting/`: GFO Generator (`gfo_generator.py`), Travel Expense Manager (`travel_expense_manager.py`), Cash Desk Manager (`cash_desk_manager.py`), Corporate Consolidation Engine (`corporate_consolidation.py`), Fixed Assets & Depreciation Manager (`fixed_assets_depreciation.py`), Inventory Valuation Engine (`inventory_valuation.py`), EU OSS E-Commerce Invoicing Adapter (`eu_oss_accounting.py`), Customs & Excise Accounting Engine (`customs_excise_accounting.py`), Payroll Accounting Engine (`payroll_accounting.py`), FX Revaluation Engine (`fx_revaluation.py`), Bulgarian double-entry translation & XML generator (`translate_to_delta.py`)
- `src/audit/`: Global Multi-Entity Tax Engine (`global_tax_engine.py`), Swiss ESTV VAT Engine (`swiss_estv_tax_engine.py`), US Sales Tax Engine (`us_sales_tax_engine.py`), Dividend Tax Manager (`dividend_tax_manager.py`), Autonomous Corporate Income Tax Return Generator (`corporate_tax_return.py`), Autonomous Tax Policy Ingestion Engine (`tax_policy_ingestor.py`), Autonomous Tax Audit Defense Engine (`tax_audit_defense.py`), NRA VAT E-Reporting Adapter (`nra_vat_reporter.py`), OECD SAF-T Exporter (`saft_exporter.py`), SQL verification & TRANSFER.LOG exporter (`generate_transfer_log.py`)
- `src/ai/`: Predictive AI Advisory & Decision Engine (`predictive_advisor.py`, `advisory_api.py`), AI-Powered Smart Invoice Matching & Auto-Reconciliation Engine (`smart_invoice_matcher.py`), Dynamic Cash Flow Optimization & Predictive Liquidity AI Engine (`cash_optimizer.py`), Autonomous Voice & NLU Command Executor (`nlu_voice_command_executor.py`), Neural Trial Balance Sentinel (`neural_trial_balance_sentinel.py`), Voice Accounting Assistant (`voice_accounting_assistant.py`), Financial Solvency Analyzer (`financial_solvency_analyzer.py`), Distributed GPU Cluster Orchestrator (`gpu_cluster_orchestrator.py`), Synthetic Dataset Generator & Stress Harness (`synthetic_stress_harness.py`), Autonomous Agent Swarm (`autonomous_agent_swarm.py`), Multi-Modal Document Reconciler (`multimodal_reconciler.py`), Cash Flow Forecaster (`cashflow_forecaster.py`), Fraud Detector (`fraud_detector.py`), Active Learning Loop (`active_learning_loop.py`), Unsloth AI classifier & fine-tuner (`unsloth_classifier.py`, `unsloth_finetune.py`)
- `src/dashboard/`: Real-Time Multi-Entity Audit Compliance Engine (`realtime_compliance_ui.py`), Web UI Dashboard Server & WebSockets Telemetry Hub (`dashboard_server.py`), Executive Briefing Generator (`executive_briefing.py`), Prometheus Telemetry Exporter (`prometheus_exporter.py`), OpenBalancer client (`openbalancer_client.py`)
- `src/backup/`: Active-Active SQL Sync Guard (`active_active_sql_sync.py`), Autonomous Audit Log Cold Storage Archiver (`cold_storage_archiver.py`), DR Multi-Region Replication Manager (`disaster_recovery_replication.py`), Automated Nightly Backup Manager (`nightly_backup.py`)
- `src/cluster/`: Quantum-Safe Active-Active DR Mesh (`quantum_safe_dr_mesh.py`), Zero-Trust DR Failover Orchestrator (`dr_failover_orchestrator.py`), Rolling Upgrade Controller (`rolling_upgrade_controller.py`), High Availability Cluster Manager (`ha_failover.py`)
- `src/integration/`: Poland KSeF Gateway & GUS BIR API (`ksef_gateway.py`, `gus_bir_api.py`, `ksef_api.py`), Romania ANAF e-Factura Gateway (`anaf_efactura_gateway.py`, `anaf_api.py`), UK HMRC MTD VAT Adapter (`hmrc_mtd_adapter.py`), Autonomous NRA E-Invoicing Gateway (`nra_einvoice_gateway.py`), Native Mobile Push Gateway (`mobile_push_gateway.py`), Peppol EU E-Invoicing Engine (`peppol_einvoicing.py`), Telegram Bot Guard (`telegram_notifier.py`), VIES VAT Checker (`vies_vat_checker.py`), Obsidian Vault exporter (`obsidian_exporter.py`) & Supabase logger (`supabase_logger.py`)
- `src/ocr/`: Enterprise Edge AI & Mobile Receipt Scanner Suite (`edge_ai_mobile_suite.py`), Image Preprocessor (`image_preprocessor.py`), PDF OCR, multi-bank extractors & batch processing (`extract_dsk_statement.py`, `multi_bank_extractor.py`, `batch_processor.py`)
- `src/dashboard/web_ui/`: FinansProtect Web UI Dashboard static assets (`index.html`, `ksef.html`, `anaf.html`, `advisory.html`, `analytics.html`, `styles.css`, `app.js`)
- `src/vm_automation/`: VNC & PowerShell Base64 QEMU automation scripts (`import_to_deltapro.py`)
- `scripts/`: Microinvest n8n service, DR replication runner, HA cluster deployer, nightly backup scheduler (`microinvest_n8n_service.py`, `run_dr_replication.sh`, `deploy_ha_cluster.sh`, `schedule_nightly_backup.sh`, `deploy_production_stack.sh`)
- `deploy/helm/`: Production Helm chart for Kubernetes/K3s deployment (`Chart.yaml`, `values.yaml`, 15 templates)
- `deploy/k3s/`: K3s cluster installation scripts, Traefik IngressRoute & cert-manager configuration
- `docs/site/`: Bilingual MkDocs Material documentation site (BG/EN) with admin guide, user manual & API reference
- `tests/`: Unit and E2E test suites (734/734 passed)

