# Phase 25 Strategic Roadmap: Romania ANAF e-Factura & Cross-Border CEE Compliance Gateway

## Vision & Objective
Phase 25 introduces an enterprise-grade **Romania ANAF e-Factura Gateway & Cross-Border CEE Compliance System** (`src/integration/anaf_efactura_gateway.py`), REST API router (`src/integration/anaf_api.py`), and interactive executive web dashboard (`src/dashboard/web_ui/anaf.html`) to FinansProtect. This milestone implements full support for Romanian national e-invoicing mandates (RO e-Factura), UBL 2.1 RO-CIUS XML document generation and schematron validation, ANAF OAuth 2.0 / SPV portal authentication flow, XMLDSig / QES digital signing, ANAF submission upload / status polling / receipt download endpoints, and real-time Romanian ANAF VAT Registry (CIF validation & TVAi status) lookup.

---

## Strategic Milestones

### Milestone M78: Romania ANAF e-Factura Gateway (`m78_romania_anaf_efactura`)
- **Objective**: Deliver a full-stack Romania ANAF e-Factura Gateway featuring UBL 2.1 RO-CIUS XML document generation and validation, Romanian CIF/CUI check digit verification, ANAF OAuth 2.0 SPV authentication, XMLDSig digital signature attachment, ANAF upload gateway, async processing status poller, receipt downloader, ANAF VAT Registry API integration (`PlatitorTvaRest`), REST API router, and interactive web UI dashboard (`src/dashboard/web_ui/anaf.html`).
- **Scope**:
  - **Romania ANAF e-Factura Gateway Engine (`src/integration/anaf_efactura_gateway.py`)**: UBL 2.1 RO-CIUS XML generation (Invoices type 380, Credit Notes 381, Debit Notes 383, Self-billing 389), Romanian CIF validation, mandatory RO-CIUS business rule validation, ANAF OAuth 2.0 SPV authentication, XMLDSig QES digital signature processing, upload submission (`/upload/FACT1`), status query (`/stareMesaje`), response download (`/descarcare`), and offline/mock test fallback engine.
  - **ANAF VAT Registry API Integration (`PlatitorTvaRest`)**: Real-time lookup against ANAF public API (`/PlatitorTvaRest/api/v8/ws/tva`) for company validation, VAT status (`scpTva`), TVAi (TVA la încasare) status, split VAT status, and address details by CIF.
  - **ANAF e-Factura REST API Router (`src/integration/anaf_api.py`)**: Endpoints (`/api/v1/anaf/health`, `/api/v1/anaf/oauth/token`, `/api/v1/anaf/invoices/generate-xml`, `/api/v1/anaf/invoices/validate`, `/api/v1/anaf/invoices/submit`, `/api/v1/anaf/invoices/status/{upload_id}`, `/api/v1/anaf/invoices/download/{download_id}`, `/api/v1/anaf/vat-registry/check`, `/api/v1/anaf/invoices`) integrated into `dashboard_server.py` and documented in `openapi_docs.py`.
  - **Interactive Web UI ANAF Dashboard (`src/dashboard/web_ui/anaf.html`)**: Responsive executive workspace featuring invoice generation form, UBL 2.1 XML live code previewer, RO-CIUS validation feedback panel, ANAF Upload & Status Tracker table, ANAF VAT Registry (CIF Lookup) tool, and multi-format action buttons.
- **Dependencies**: M12, M19, M41, M60, M77
- **Target Deliverables**: `src/integration/anaf_efactura_gateway.py`, `src/integration/anaf_api.py`, `src/dashboard/web_ui/anaf.html`, `tests/integration/test_anaf_efactura_gateway.py`, `tests/integration/test_anaf_api.py`, `tests/dashboard/test_anaf_dashboard.py`
- **Status**: DONE

---

## Verification Criteria
- M78: 100% test coverage across `tests/integration/test_anaf_efactura_gateway.py`, `tests/integration/test_anaf_api.py`, and `tests/dashboard/test_anaf_dashboard.py`; REST API endpoints respond with valid ANAF e-Factura payloads; Web UI dashboard loads and renders interactive forms and status tables; UBL 2.1 RO-CIUS XML complies with schema and business rules.
