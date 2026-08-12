# Strategic Expansion Roadmap - Phase 3 (Post-M10 Milestones)

## 📌 Context
With Milestones M1 through M10 100% completed, verified (163/163 passing tests), containerized, and integrated across `macmini-primary`, `macmini-secondary`, and the Windows 11 QEMU VM, the following strategic expansion milestones are recommended for next phase execution:

---

## 🎯 Proposed Milestones

### 1. **M11: Multi-Bank OCR Expansion (UniCredit, UBB, Postbank)**
- **Scope**: Extend `src/ocr/` with template extractions for UniCredit Bulbank, UBB (United Bulgarian Bank), and Postbank PDF statements.
- **Benefit**: Broadens system compatibility across all major Bulgarian commercial banks.

### 2. **M12: Web UI Real-Time Audit Dashboard (FinansProtect UI)**
- **Scope**: Build a modern web application (React/Vite) displaying:
  - Live bank statement intake queue status
  - Processed EUR turnover metrics and debit/credit totals
  - SHA-256 audit integrity logs
  - Real-time VNC preview of the QEMU Windows 11 VM and Microinvest Delta Pro
- **Benefit**: Provides visual monitoring for accounting managers and auditors.

### 3. **M13: Automated Nightly Database & Log Snapshot Backup**
- **Scope**: Schedule daily cron backup jobs for:
  - MS SQL Server (`SQLEXPRESS`) database snapshots (`DeltaPro.bak`)
  - Persistent `C:\TRANSFER.LOG` audit log files
  - Infisical Vault secrets backups to S3 / encrypted storage
- **Benefit**: Guarantees zero data loss and business continuity compliance.

### 4. **M14: Active Learning Feedback Loop for Unsloth AI**
- **Scope**: Create an active learning pipeline where accountant overrides or corrections in Microinvest Delta Pro automatically generate new instruction-tuning samples to continuously fine-tune the Unsloth LLM model.
- **Benefit**: Achieves 99.99% double-entry account classification accuracy over time.
