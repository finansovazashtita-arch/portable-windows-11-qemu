"""
M82 Hungary NAV Online Számla 3.0 REST API Router.

Provides lightweight HTTP handler functions for the NAV gateway endpoints,
callable from the FinansProtect dashboard server without any external framework.

Endpoints:
  GET  /api/nav/health           — Gateway health check
  POST /api/nav/validate-tax     — Validate Hungarian adószám
  POST /api/nav/token-exchange   — Authenticate & obtain session token
  POST /api/nav/generate-xml     — Generate InvoiceData XML (no submission)
  POST /api/nav/submit-invoice   — Submit invoice to NAV
  POST /api/nav/query-status     — Query transaction status
  POST /api/nav/query-taxpayer   — Look up taxpayer by tax number
  POST /api/nav/journal-entries  — Generate Hungarian double-entry entries
  GET  /api/nav/invoices         — List submitted invoices
  GET  /api/nav/statistics       — Gateway statistics
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.integration.nav_gateway import (
    NAVCredentials,
    NAVDoubleEntryMapper,
    NAVEnvironment,
    NAVInvoice,
    NAVInvoiceAppearance,
    NAVInvoiceCategory,
    NAVInvoiceGenerator,
    NAVInvoiceLineItem,
    NAVInvoiceOperation,
    NAVInvoiceStatus,
    NAVOnlineSzamlaGateway,
    NAVPaymentMethod,
    NAVRequestSigner,
    NAVTaxpayer,
    NAVVATRate,
    NAVXMLDSigSigner,
    format_tax_number,
    validate_tax_number,
)

logger = logging.getLogger("nav_api")

# ---------------------------------------------------------------------------
# Shared gateway instance (singleton per environment)
# ---------------------------------------------------------------------------

_gateway_sandbox: Optional[NAVOnlineSzamlaGateway] = None
_gateway_production: Optional[NAVOnlineSzamlaGateway] = None


def _get_gateway(environment: str = "SANDBOX") -> NAVOnlineSzamlaGateway:
    """Return a shared gateway instance for the requested environment."""
    global _gateway_sandbox, _gateway_production

    env = NAVEnvironment.PRODUCTION if environment.upper() == "PRODUCTION" else NAVEnvironment.SANDBOX

    if env == NAVEnvironment.SANDBOX:
        if _gateway_sandbox is None:
            _gateway_sandbox = NAVOnlineSzamlaGateway(environment=NAVEnvironment.SANDBOX)
        return _gateway_sandbox
    else:
        if _gateway_production is None:
            _gateway_production = NAVOnlineSzamlaGateway(environment=NAVEnvironment.PRODUCTION)
        return _gateway_production


def _parse_json_body(raw_body: str) -> Dict[str, Any]:
    """Parse JSON request body, return empty dict on failure."""
    try:
        return json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _success(data: Any, message: str = "OK") -> Dict[str, Any]:
    return {
        "status": "success",
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


def _error(message: str, code: str = "ERROR") -> Dict[str, Any]:
    return {
        "status": "error",
        "error_code": code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _parse_taxpayer(d: Dict) -> NAVTaxpayer:
    """Construct NAVTaxpayer from API dict payload."""
    return NAVTaxpayer(
        tax_number=d.get("tax_number", "12345678-2-41"),
        name=d.get("name", ""),
        bank_account_number=d.get("bank_account_number", ""),
        address_country=d.get("address_country", "HU"),
        address_region=d.get("address_region", ""),
        address_postal_code=d.get("address_postal_code", ""),
        address_city=d.get("address_city", ""),
        address_street=d.get("address_street", ""),
        vat_status=d.get("vat_status", "DOMESTIC"),
    )


def _parse_line_item(d: Dict, idx: int) -> NAVInvoiceLineItem:
    """Construct NAVInvoiceLineItem from API dict payload."""
    vat_str = str(d.get("vat_rate", "27")).upper()
    try:
        vat_rate = NAVVATRate(vat_str)
    except ValueError:
        vat_rate = NAVVATRate.RATE_27

    item = NAVInvoiceLineItem(
        line_number=d.get("line_number", idx),
        description=d.get("description", f"Tétel {idx}"),
        quantity=float(d.get("quantity", 1.0)),
        unit_of_measure=d.get("unit_of_measure", "PIECE"),
        unit_price_huf=float(d.get("unit_price_huf", 0.0)),
        vat_rate=vat_rate,
        product_code=d.get("product_code", ""),
    )
    item.calculate_totals()
    return item


def _build_invoice_from_payload(payload: Dict) -> NAVInvoice:
    """Construct NAVInvoice from API request payload."""
    supplier_data = payload.get("supplier", {})
    customer_data = payload.get("customer", {})
    items_data = payload.get("items", [])

    supplier = _parse_taxpayer(supplier_data)
    customer = _parse_taxpayer(customer_data)
    items = [_parse_line_item(item, idx + 1) for idx, item in enumerate(items_data)]

    # Default dates to today if not provided
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Parse operation
    operation_str = str(payload.get("operation", "CREATE")).upper()
    try:
        operation = NAVInvoiceOperation(operation_str)
    except ValueError:
        operation = NAVInvoiceOperation.CREATE

    # Parse category
    category_str = str(payload.get("category", "NORMAL")).upper()
    try:
        category = NAVInvoiceCategory(category_str)
    except ValueError:
        category = NAVInvoiceCategory.NORMAL

    # Parse payment method
    payment_str = str(payload.get("payment_method", "TRANSFER")).upper()
    try:
        payment_method = NAVPaymentMethod(payment_str)
    except ValueError:
        payment_method = NAVPaymentMethod.TRANSFER

    return NAVInvoice(
        invoice_number=payload.get("invoice_number", f"FP-NAV-{today}-001"),
        invoice_issue_date=payload.get("invoice_issue_date", today),
        payment_date=payload.get("payment_date", today),
        delivery_date=payload.get("delivery_date", today),
        supplier=supplier,
        customer=customer,
        items=items,
        operation=operation,
        category=category,
        payment_method=payment_method,
        currency_code=payload.get("currency_code", "HUF"),
        exchange_rate=float(payload.get("exchange_rate", 1.0)),
        nav_annul_reference=payload.get("nav_annul_reference", ""),
        language=payload.get("language", "HU"),
    )


# ---------------------------------------------------------------------------
# HANDLER FUNCTIONS
# ---------------------------------------------------------------------------

def get_nav_health_handler(query_params: Dict = None) -> Dict[str, Any]:
    """
    GET /api/nav/health
    Returns NAV gateway health and configuration status.
    """
    try:
        gw = _get_gateway("SANDBOX")
        stats = gw.get_statistics()
        return _success({
            "gateway_status":  "OPERATIONAL",
            "schema_version":  "3.0",
            "environment":     "SANDBOX",
            "session_active":  stats["session_active"],
            "total_invoices":  stats["total_invoices"],
            "api_endpoints": {
                "sandbox":    "https://api-test.onlineszamla.nav.gov.hu/invoiceService/v3",
                "production": "https://api.onlineszamla.nav.gov.hu/invoiceService/v3",
            },
            "features": [
                "SHA-3-512 request signatures",
                "XMLDSig invoice signing",
                "HUF monetary precision",
                "Token exchange (tokenExchange)",
                "Invoice submission (manageInvoice)",
                "Invoice status query",
                "Taxpayer query",
                "Hungarian double-entry journal entries",
            ],
        }, "NAV Online Számla 3.0 Gateway is operational")
    except Exception as exc:
        logger.exception("Health check failed")
        return _error(f"Health check failed: {exc}", "HEALTH_CHECK_ERROR")


def post_nav_validate_tax_handler(raw_body: str) -> Dict[str, Any]:
    """
    POST /api/nav/validate-tax
    Body: {"tax_number": "12345678-2-41"}
    Validates a Hungarian tax number (adószám) using Modulo 11.
    """
    payload = _parse_json_body(raw_body)
    tax_number = payload.get("tax_number", "").strip()

    if not tax_number:
        return _error("tax_number is required", "MISSING_FIELD")

    is_valid = validate_tax_number(tax_number)
    clean = format_tax_number(tax_number) if is_valid else ""

    return _success({
        "tax_number":       tax_number,
        "clean_tax_number": clean,
        "hu_vat_number":    f"HU{clean}" if clean else "",
        "is_valid":         is_valid,
        "validation_method": "Modulo 11 check digit (Hungarian adószám)",
        "format_note": (
            "Valid Hungarian adószám: 8-digit core or 11-digit full (XXXXXXXX-Y-ZZ). "
            "Check digit = SUM(digit × weight[9,7,3,1,9,7,3]) MOD 10."
        ),
    }, "Tax number validation complete")


def post_nav_token_exchange_handler(raw_body: str) -> Dict[str, Any]:
    """
    POST /api/nav/token-exchange
    Body: {"environment": "SANDBOX", "login": "...", "password": "...", "tax_number": "..."}
    Exchange credentials for a NAV session token.
    """
    payload = _parse_json_body(raw_body)
    environment = payload.get("environment", "SANDBOX")

    try:
        gw = _get_gateway(environment)
        session = gw.exchange_token()
        return _success({
            "token":        session.token_value[:32] + "...",  # Truncate for security
            "expires_in":   session.expires_in,
            "session_valid": session.is_valid(),
            "environment":  environment,
            "note": "Session token valid for 5 minutes per NAV Online Számla 3.0 specification.",
        }, "NAV session token exchanged successfully")
    except Exception as exc:
        logger.exception("Token exchange failed")
        return _error(f"Token exchange failed: {exc}", "TOKEN_EXCHANGE_ERROR")


def post_nav_generate_xml_handler(raw_body: str) -> Dict[str, Any]:
    """
    POST /api/nav/generate-xml
    Body: invoice payload dict (see _build_invoice_from_payload)
    Generate InvoiceData XML without submitting to NAV.
    """
    payload = _parse_json_body(raw_body)

    try:
        invoice = _build_invoice_from_payload(payload)
        invoice.calculate_totals()

        # Generate raw InvoiceData XML
        invoice_xml = NAVInvoiceGenerator.generate_invoice_data_xml(invoice)

        # Optionally wrap in XMLDSig
        include_sig = payload.get("include_xmldsig", True)
        if include_sig:
            timestamp = NAVRequestSigner.current_timestamp()
            signed_xml = NAVXMLDSigSigner.sign_invoice_xml(
                invoice_xml, invoice.invoice_number, timestamp
            )
        else:
            signed_xml = invoice_xml

        # Build summary
        request_id = NAVRequestSigner.generate_request_id()
        timestamp  = NAVRequestSigner.current_timestamp()
        request_sig = NAVRequestSigner.compute_request_signature(
            request_id, timestamp, "DEMO-KEY"
        )

        return _success({
            "invoice_number":       invoice.invoice_number,
            "xml_content":          signed_xml,
            "xml_size_bytes":       len(signed_xml.encode("utf-8")),
            "invoice_net_huf":      int(round(invoice.invoice_net_amount)),
            "invoice_vat_huf":      int(round(invoice.invoice_vat_amount)),
            "invoice_gross_huf":    int(round(invoice.invoice_gross_amount)),
            "line_count":           len(invoice.items),
            "vat_summary":          {k: {
                "net_huf":   int(round(v["net"])),
                "vat_huf":   int(round(v["vat"])),
                "gross_huf": int(round(v["gross"])),
            } for k, v in invoice.vat_summary.items()},
            "includes_xmldsig":     include_sig,
            "sample_request_id":    request_id,
            "sample_timestamp":     timestamp,
            "sample_signature_sha3_512": request_sig[:32] + "...",
            "schema_namespace":     "http://schemas.nav.gov.hu/OSA/3.0/data",
        }, "InvoiceData XML generated successfully")
    except Exception as exc:
        logger.exception("XML generation failed")
        return _error(f"XML generation failed: {exc}", "XML_GEN_ERROR")


def post_nav_submit_invoice_handler(raw_body: str) -> Dict[str, Any]:
    """
    POST /api/nav/submit-invoice
    Body: {"environment": "SANDBOX", "invoice": {...invoice payload...}}
    Submit an invoice to NAV Online Számla.
    """
    payload = _parse_json_body(raw_body)
    environment = payload.get("environment", "SANDBOX")
    invoice_data = payload.get("invoice", payload)

    try:
        invoice = _build_invoice_from_payload(invoice_data)
        gw = _get_gateway(environment)
        result = gw.submit_invoice(invoice)

        return _success({
            "transaction_id":    result.transaction_id,
            "invoice_number":    result.invoice_number,
            "status":            result.status.value,
            "index_in_batch":    result.index_in_batch,
            "original_request_id": result.original_request_id,
            "timestamp":         result.timestamp,
            "invoice_net_huf":   int(round(invoice.invoice_net_amount)),
            "invoice_vat_huf":   int(round(invoice.invoice_vat_amount)),
            "invoice_gross_huf": int(round(invoice.invoice_gross_amount)),
            "environment":       environment,
        }, f"Invoice {result.invoice_number} submitted successfully to NAV")
    except ValueError as exc:
        return _error(str(exc), "VALIDATION_ERROR")
    except Exception as exc:
        logger.exception("Invoice submission failed")
        return _error(f"Invoice submission failed: {exc}", "SUBMISSION_ERROR")


def post_nav_query_status_handler(raw_body: str) -> Dict[str, Any]:
    """
    POST /api/nav/query-status
    Body: {"transaction_id": "HU-NAV-...", "environment": "SANDBOX"}
    Query the processing status of a submitted invoice transaction.
    """
    payload = _parse_json_body(raw_body)
    transaction_id = payload.get("transaction_id", "").strip()
    environment = payload.get("environment", "SANDBOX")

    if not transaction_id:
        return _error("transaction_id is required", "MISSING_FIELD")

    try:
        gw = _get_gateway(environment)
        status_info = gw.query_invoice_status(transaction_id)
        return _success(status_info, "Invoice status queried successfully")
    except Exception as exc:
        logger.exception("Status query failed")
        return _error(f"Status query failed: {exc}", "STATUS_QUERY_ERROR")


def post_nav_query_taxpayer_handler(raw_body: str) -> Dict[str, Any]:
    """
    POST /api/nav/query-taxpayer
    Body: {"tax_number": "12345678-2-41", "environment": "SANDBOX"}
    Look up a taxpayer's registration data from NAV.
    """
    payload = _parse_json_body(raw_body)
    tax_number = payload.get("tax_number", "").strip()
    environment = payload.get("environment", "SANDBOX")

    if not tax_number:
        return _error("tax_number is required", "MISSING_FIELD")

    try:
        gw = _get_gateway(environment)
        info = gw.query_taxpayer(tax_number)
        return _success({
            "tax_number":    info.tax_number,
            "company_name":  info.company_name,
            "is_valid":      info.is_valid,
            "tax_validity":  info.tax_validity,
            "vat_status":    info.vat_status,
            "address":       info.address,
            "query_timestamp": info.query_timestamp,
        }, "Taxpayer data retrieved from NAV")
    except Exception as exc:
        logger.exception("Taxpayer query failed")
        return _error(f"Taxpayer query failed: {exc}", "TAXPAYER_QUERY_ERROR")


def post_nav_journal_entries_handler(raw_body: str) -> Dict[str, Any]:
    """
    POST /api/nav/journal-entries
    Body: {invoice payload}
    Generate Hungarian double-entry journal entries for an invoice.
    """
    payload = _parse_json_body(raw_body)

    try:
        invoice = _build_invoice_from_payload(payload)
        invoice.calculate_totals()
        entries = NAVDoubleEntryMapper.generate_journal_entries(invoice)

        return _success({
            "invoice_number": invoice.invoice_number,
            "operation":      invoice.operation.value,
            "currency":       invoice.currency_code,
            "journal_entries": entries,
            "entry_count":    len(entries),
            "total_net_huf":  int(round(invoice.invoice_net_amount)),
            "total_vat_huf":  int(round(invoice.invoice_vat_amount)),
            "total_gross_huf": int(round(invoice.invoice_gross_amount)),
            "accounting_standard": "SZT (Magyar Számviteli Törvény) 2000. évi C. törvény",
            "chart_of_accounts": {
                "311": "Belföldi vevők (domestic trade receivables)",
                "319": "Külföldi vevők (foreign trade receivables)",
                "454": "Fizetendő ÁFA (VAT payable)",
                "701": "Belföldi értékesítés nettó árbevétele (domestic sales revenue)",
                "702": "Export értékesítés (export sales revenue)",
            },
        }, "Hungarian double-entry journal entries generated")
    except Exception as exc:
        logger.exception("Journal entry generation failed")
        return _error(f"Journal entry generation failed: {exc}", "JOURNAL_ERROR")


def get_nav_invoices_handler(query_params: Dict = None) -> Dict[str, Any]:
    """
    GET /api/nav/invoices
    List submitted invoices. Optional query param: ?status=ACCEPTED&environment=SANDBOX
    """
    params = query_params or {}
    environment = params.get("environment", "SANDBOX")
    status_filter = params.get("status", "").upper()

    try:
        gw = _get_gateway(environment)
        status_enum = None
        if status_filter:
            try:
                status_enum = NAVInvoiceStatus(status_filter)
            except ValueError:
                pass

        invoices = gw.list_invoices(status=status_enum, limit=200)
        invoice_list = []
        for inv in invoices:
            invoice_list.append({
                "invoice_number":    inv.invoice_number,
                "issue_date":        inv.invoice_issue_date,
                "supplier_name":     inv.supplier.name,
                "customer_name":     inv.customer.name,
                "operation":         inv.operation.value,
                "status":            inv.status.value,
                "net_huf":           int(round(inv.invoice_net_amount)),
                "vat_huf":           int(round(inv.invoice_vat_amount)),
                "gross_huf":         int(round(inv.invoice_gross_amount)),
                "transaction_id":    inv.nav_transaction_id,
                "currency":          inv.currency_code,
            })

        return _success({
            "invoices":          invoice_list,
            "total":             len(invoice_list),
            "environment":       environment,
            "status_filter":     status_filter or "ALL",
        }, f"Retrieved {len(invoice_list)} invoice(s)")
    except Exception as exc:
        logger.exception("Invoice listing failed")
        return _error(f"Invoice listing failed: {exc}", "LIST_ERROR")


def get_nav_statistics_handler(query_params: Dict = None) -> Dict[str, Any]:
    """
    GET /api/nav/statistics
    Return NAV gateway operational statistics.
    """
    params = query_params or {}
    environment = params.get("environment", "SANDBOX")

    try:
        gw = _get_gateway(environment)
        stats = gw.get_statistics()
        return _success(stats, "NAV gateway statistics retrieved")
    except Exception as exc:
        logger.exception("Statistics retrieval failed")
        return _error(f"Statistics retrieval failed: {exc}", "STATS_ERROR")
