# Enterprise Governance & Production Expansion Roadmap - Phase 4 (Post-M14 Milestones)

## 📌 Context
With Milestones M1 through M14 100% completed, verified (175/175 passing tests), containerized, and integrated across `macmini-primary`, `macmini-secondary`, and the Windows 11 QEMU VM, the following Phase 4 initiatives are recommended for future enterprise deployment:

---

## 🎯 Proposed Milestones

### 1. **M15: Multi-Tenant Enterprise Isolation & Role-Based Access Control (RBAC)**
- **Scope**: Multi-company support enabling separate accounting firms or corporate clients to isolate statement queues, chart of accounts, and audit logs with JWT role-based access control.
- **Benefit**: Empowers multi-client accounting practices and corporate groups to run on a single cluster securely.

### 2. **M16: Automated E-Invoicing & VIES VAT API Sync**
- **Scope**: Live integration with NRA / НАП e-invoicing APIs and European VIES VAT validation services to automatically cross-check counterparty VAT numbers and tax statuses.
- **Benefit**: Guarantees tax compliance and automates VAT registration verification.

### 3. **M17: Advanced Anomaly Detection & Fraud Prevention Guardrails**
- **Scope**: ML anomaly detection engine flagging suspicious transactions, unverified IBANs, sudden amount spikes, or cross-bank duplicate invoices before Microinvest import.
- **Benefit**: Prevents fraud, human error, and duplicate payments.

### 4. **M18: High Availability (HA) Failover & Clustering**
- **Scope**: Multi-node HA cluster orchestration across `macmini-primary` and `macmini-secondary` with automated VNC reconnect, database replication, and failover routing.
- **Benefit**: Provides 99.99% uptime for mission-critical accounting workflows.
