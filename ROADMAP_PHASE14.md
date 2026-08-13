# Roadmap Phase 14: Corporate Income Tax, Dividends & Real-Time Bank Guard

## Proposed Next Milestones (Phase 14)

### M51: Autonomous Corporate Income Tax (CITA / ЗКПО) Tax Return Generator
- **Objective**: Automate annual corporate income tax calculations and tax return preparation under Art. 92 CITA (Чл. 92 ЗКПО).
- **Key Features**:
  - 10% flat corporate tax rate calculation on taxable profit.
  - Tax adjustments for non-deductible expenses (609) and tax depreciation schedule (Category I-VII).
  - Statutory NRA XML / TXT tax return file generation.

### M52: Autonomous Personal Income Tax & Dividend Withholding Tax Manager
- **Objective**: Automate dividend withholding tax calculation (5%) and NRA Form 55 quarterly reporting.
- **Key Features**:
  - Withholding tax journal entries (Debit 122 / Credit 454).
  - Quarterly NRA Form 55 filing declaration generation.

### M53: Automated Real-Time Bank Account Reconciliation Guard
- **Objective**: Continuous sub-second reconciliation of bank account feeds against Account 503.
- **Key Features**:
  - Automated flag for unposted bank transfers and pending uncleared deposits.
  - Real-time ledger balance vs. bank statement balance validation.
