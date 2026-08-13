# Phase 26 Strategic Roadmap: Poland KSeF, Greece myDATA & Enterprise ESG Sustainability Gateway

## Vision & Objective
Phase 26 expands **FinansProtect** into complete CEE (Central & Eastern Europe) and Southern European statutory tax compliance, as well as Enterprise ESG & Carbon Tax accounting. Following the successful deployment of the Romania ANAF e-Factura Gateway (M78), Phase 26 introduces native integration with Poland's **KSeF (Krajowy System e-Faktur)**, Greece's **myDATA (Independent Authority for Public Revenue - AADE)**, and an **Enterprise ESG Sustainability Accounting & CBAM (Carbon Border Adjustment Mechanism) Calculator**.

---

## Strategic Milestones

### Milestone M79: Poland KSeF e-Fakturowanie Gateway (`m79_poland_ksef_gateway`)
- **Objective**: Implement end-to-end integration with Poland's mandatory KSeF (Krajowy System e-Faktur) platform, including FA(2)/FA(3) UBL/XML invoice generation, NIP (Numer Identyfikacji Podatkowej) tax validation, OAuth 2.0 / Session Token authentication with the Polish Ministry of Finance API, XAdES / QES signature attachment, invoice submission, status polling, and official KSeF receipt (UPO - Urzędowe Poświadczenie Odbioru) archiving.
- **Scope**:
  - **Poland KSeF Gateway Engine (`src/integration/ksef_gateway.py`)**: Polish FA(2)/FA(3) structured XML invoice generator, Polish NIP check-digit verification, KSeF Session challenge/response authentication flow, XAdES digital signature wrapper, batch submission handler (`/online/Invoice/Send`), asynchronous processing status poller, and UPO downloader.
  - **Polish GUS Bir API Integration (`src/integration/gus_bir_api.py`)**: Real-time company metadata and REGON/NIP lookup via the Polish Central Statistical Office (GUS) BIR1.1 web service API.
  - **KSeF REST API Router (`src/integration/ksef_api.py`)**: Endpoints (`/api/v1/ksef/health`, `/api/v1/ksef/auth/session`, `/api/v1/ksef/invoices/generate-xml`, `/api/v1/ksef/invoices/submit`, `/api/v1/ksef/invoices/status/{reference_number}`, `/api/v1/ksef/invoices/upo/{ksef_number}`, `/api/v1/ksef/gus/check`) integrated into `dashboard_server.py` and documented in OpenAPI 3.1.
  - **Interactive Web UI KSeF Dashboard (`src/dashboard/web_ui/ksef.html`)**: Responsive management UI with invoice creation, XML preview, UPO verification table, and GUS company lookup tool.
- **Dependencies**: M12, M19, M41, M60, M77, M78
- **Target Deliverables**: `src/integration/ksef_gateway.py`, `src/integration/gus_bir_api.py`, `src/integration/ksef_api.py`, `src/dashboard/web_ui/ksef.html`, test suites.
- **Status**: Completed (Phase 26)

---

### Milestone M80: Greece myDATA Compliance Gateway (`m80_greece_mydata_gateway`)
- **Objective**: Deliver direct e-bookkeeping and e-invoicing transmission to the Independent Authority for Public Revenue (AADE myDATA) in Greece. Features XML document schema validation (Sales Invoices, Expense Classification, Payroll), AFM (ΑΦΜ) tax ID validation, REST API transmission to AADE, MARK unique registration number assignment, and automatic double-entry journal entry synchronization.
- **Scope**:
  - **Greece myDATA Engine (`src/integration/mydata_gateway.py`)**: AADE myDATA XML document builder for income/expenses, Greek AFM checksum validator, AADE REST API authentication via `aade-user-id` and `subscription-key`, `SendInvoices` / `SendExpenses` endpoints, MARK number tracking, and error handling for statutory code rejections.
  - **myDATA REST API Router (`src/integration/mydata_api.py`)**: Endpoints (`/api/v1/mydata/health`, `/api/v1/mydata/send-invoices`, `/api/v1/mydata/send-expenses`, `/api/v1/mydata/incomes/request`, `/api/v1/mydata/cancel/{mark}`) integrated into the core dashboard server.
  - **Interactive Web UI myDATA Dashboard (`src/dashboard/web_ui/mydata.html`)**: Responsive workspace for transmitting income/expenses, monitoring MARK statuses, and reviewing tax classifications.
- **Dependencies**: M12, M19, M41, M60, M77, M78
- **Target Deliverables**: `src/integration/mydata_gateway.py`, `src/integration/mydata_api.py`, `src/dashboard/web_ui/mydata.html`, test suites.
- **Status**: Completed (Phase 26)

---

### Milestone M81: Enterprise ESG Sustainability & Carbon Tax Accounting Engine (`m81_esg_carbon_accounting`)
- **Objective**: Implement GHG Protocol (Scope 1, Scope 2, and Scope 3) carbon footprint calculation and EU CBAM (Carbon Border Adjustment Mechanism) tax accounting integrated directly into double-entry purchase ledgers. Converts energy, fuel, and raw material invoices into tCO2e emissions metrics, calculates carbon tax liabilities, posts double-entry journal entries (Account 609 / Account 454), and exports CSRD (Corporate Sustainability Reporting Directive) compliant reports.
- **Scope**:
  - **ESG & Carbon Footprint Calculation Engine (`src/accounting/esg_carbon_accounting.py`)**: Automated conversion of purchase journal items (kWh electricity, liters fuel, tons steel/aluminum) into CO2 equivalent metrics using DEFRA/IEA emission factors, CBAM embedded emission calculations for imported goods, carbon tax liability estimator, and double-entry accounting mapper.
  - **ESG & Carbon REST API Router (`src/analytics/esg_api.py`)**: Endpoints (`/api/v1/esg/footprint/calculate`, `/api/v1/esg/cbam/report`, `/api/v1/esg/journals/post`, `/api/v1/esg/csrd/export`) integrated into `dashboard_server.py`.
  - **Interactive Web UI ESG & Carbon Dashboard (`src/dashboard/web_ui/esg.html`)**: Executive sustainability overview with Scope 1-3 emission charts, CBAM tax projections, and CSRD export controls.
- **Dependencies**: M12, M19, M41, M48, M76, M77
- **Target Deliverables**: `src/accounting/esg_carbon_accounting.py`, `src/analytics/esg_api.py`, `src/dashboard/web_ui/esg.html`, test suites.
- **Status**: Completed (Phase 26)

---

## Verification Criteria & Metrics
- 100% test coverage across all new test suites for M79, M80, and M81.
- KSeF FA(2)/FA(3) and myDATA XML schemas pass official validation without errors.
- ESG engine correctly calculates Scope 1-3 tCO2e emissions and generates balanced double-entry carbon tax journal entries.
- Web UI dashboards load seamlessly with real-time API integrations and interactive forms.
