"""
M78 Romania ANAF e-Factura REST API Router & Handlers.

Exposes RESTful API endpoints for:
- Gateway health & status checking (/api/v1/anaf/health)
- OAuth 2.0 token generation & refresh (/api/v1/anaf/oauth/token)
- UBL 2.1 RO-CIUS XML document generation (/api/v1/anaf/invoices/generate-xml)
- RO-CIUS business rule validation (/api/v1/anaf/invoices/validate)
- ANAF e-Factura upload submission (/api/v1/anaf/invoices/submit)
- Processing status polling (/api/v1/anaf/invoices/status/{upload_id})
- Receipt XML download (/api/v1/anaf/invoices/download/{download_id})
- ANAF VAT Registry & CIF verification (/api/v1/anaf/vat-registry/check)
- Invoice records query & search (/api/v1/anaf/invoices)
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.integration.anaf_efactura_gateway import (
    ANAFEInvoiceGateway,
    ANAFInvoice,
    ANAFParty,
    ANAFInvoiceItem,
    ANAFInvoiceType,
    ANAFInvoiceStatus,
    VATCategory,
    ANAFEnvironment,
    validate_cif
)

logger = logging.getLogger("anaf_api")

# Global ANAF Gateway Instance
ANAF_GATEWAY = ANAFEInvoiceGateway(environment=ANAFEnvironment.TEST)
_STORED_INVOICES: Dict[str, ANAFInvoice] = {}


def _parse_party(party_dict: Dict[str, Any], default_country: str = "RO") -> ANAFParty:
    """Helper to convert JSON dictionary to ANAFParty."""
    return ANAFParty(
        cif=party_dict.get("cif", "RO12345678"),
        name=party_dict.get("name", "Company SRL"),
        trade_register_no=party_dict.get("trade_register_no", ""),
        address=party_dict.get("address", ""),
        city=party_dict.get("city", ""),
        county=party_dict.get("county", ""),
        zip_code=party_dict.get("zip_code", ""),
        country_code=party_dict.get("country_code", default_country),
        iban=party_dict.get("iban", ""),
        bank_name=party_dict.get("bank_name", ""),
        vat_registered=party_dict.get("vat_registered", True),
        tvai_active=party_dict.get("tvai_active", False)
    )


def _parse_invoice_items(items_list: List[Dict[str, Any]]) -> List[ANAFInvoiceItem]:
    """Helper to convert JSON array to ANAFInvoiceItem list."""
    res = []
    for idx, item in enumerate(items_list, start=1):
        vat_cat_str = item.get("vat_category", "S")
        try:
            vat_cat = VATCategory(vat_cat_str)
        except ValueError:
            vat_cat = VATCategory.STANDARD

        res.append(ANAFInvoiceItem(
            line_id=str(item.get("line_id", idx)),
            description=item.get("description", f"Service / Product {idx}"),
            quantity=float(item.get("quantity", 1.0)),
            unit_of_measure=item.get("unit_of_measure", "H87"),
            unit_price=float(item.get("unit_price", 0.0)),
            net_amount=float(item.get("net_amount", 0.0)),
            vat_rate=float(item.get("vat_rate", 19.0)),
            vat_category=vat_cat,
            vat_amount=float(item.get("vat_amount", 0.0)),
            cpv_code=item.get("cpv_code", ""),
            nc_code=item.get("nc_code", "")
        ))
    return res


def _parse_invoice_payload(payload: Dict[str, Any]) -> ANAFInvoice:
    """Helper to convert JSON payload into an ANAFInvoice object."""
    supp_dict = payload.get("supplier", {})
    cust_dict = payload.get("customer", {})

    supplier = _parse_party(supp_dict, "RO")
    customer = _parse_party(cust_dict, "RO")
    items = _parse_invoice_items(payload.get("items", []))

    inv_type_str = payload.get("invoice_type", "380")
    try:
        inv_type = ANAFInvoiceType(inv_type_str)
    except ValueError:
        inv_type = ANAFInvoiceType.INVOICE_380

    return ANAFInvoice(
        invoice_id=payload.get("invoice_id", f"INV-RO-{int(datetime.now(timezone.utc).timestamp())}"),
        series=payload.get("series", "ROFPS"),
        number=payload.get("number", "1001"),
        issue_date=payload.get("issue_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        due_date=payload.get("due_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        supplier=supplier,
        customer=customer,
        items=items,
        invoice_type=inv_type,
        currency=payload.get("currency", "RON"),
        exchange_rate_ron=float(payload.get("exchange_rate_ron", 1.0)),
        payment_means=payload.get("payment_means", "42"),
        payment_terms=payload.get("payment_terms", "Net 30"),
        notes=payload.get("notes", "")
    )


# --- REST API HANDLER FUNCTIONS ---

def get_anaf_health_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handles GET /api/v1/anaf/health requests."""
    token_status = "VALID" if (ANAF_GATEWAY.token and ANAF_GATEWAY.token.is_valid()) else "NOT_AUTHENTICATED"
    return {
        "status": "ONLINE",
        "service": "Romania ANAF e-Factura Gateway",
        "environment": ANAF_GATEWAY.environment.value,
        "ro_cius_specification": "1.0.1",
        "qes_certificate_serial": ANAF_GATEWAY.certificate_serial,
        "oauth_status": token_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def post_anaf_oauth_token_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/anaf/oauth/token requests."""
    auth_code = payload.get("auth_code", "mock_auth_code_spv_2026")
    token = ANAF_GATEWAY.authenticate_oauth(auth_code=auth_code)

    return {
        "status": "success",
        "token_type": token.token_type,
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
        "expires_in": token.expires_in,
        "scope": token.scope
    }


def post_anaf_generate_xml_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/anaf/invoices/generate-xml requests."""
    invoice = _parse_invoice_payload(payload)
    validation = ANAF_GATEWAY.validate_ro_cius_rules(invoice)
    xml_content = ANAF_GATEWAY.generate_ro_cius_xml(invoice)

    _STORED_INVOICES[invoice.invoice_id] = invoice

    return {
        "status": "success" if validation["valid"] else "validation_warnings",
        "invoice_id": invoice.invoice_id,
        "valid": validation["valid"],
        "validation_errors": validation["errors"],
        "validation_warnings": validation["warnings"],
        "total_net_ron": invoice.total_net_amount,
        "total_vat_ron": invoice.total_vat_amount,
        "total_payable_ron": invoice.total_payable_amount,
        "ubl_xml": xml_content
    }


def post_anaf_validate_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/anaf/invoices/validate requests."""
    invoice = _parse_invoice_payload(payload)
    validation = ANAF_GATEWAY.validate_ro_cius_rules(invoice)

    return {
        "status": "success",
        "invoice_id": invoice.invoice_id,
        "valid": validation["valid"],
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "ro_cius_version": validation["ro_cius_version"]
    }


def post_anaf_submit_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/anaf/invoices/submit requests."""
    invoice = _parse_invoice_payload(payload)
    res = ANAF_GATEWAY.upload_invoice(invoice)
    _STORED_INVOICES[invoice.invoice_id] = invoice

    return {
        "status": "success" if res["success"] else "error",
        "invoice_id": invoice.invoice_id,
        "upload_id": res.get("upload_id"),
        "download_id": res.get("download_id"),
        "anaf_status": res.get("status"),
        "message": res.get("message"),
        "audit_hash": res.get("audit_hash")
    }


def get_anaf_status_handler(upload_id: str) -> Dict[str, Any]:
    """Handles GET /api/v1/anaf/invoices/status/{upload_id} requests."""
    res = ANAF_GATEWAY.query_processing_status(upload_id)
    return {
        "status": "success",
        "data": res
    }


def get_anaf_download_handler(download_id: str) -> Dict[str, Any]:
    """Handles GET /api/v1/anaf/invoices/download/{download_id} requests."""
    res = ANAF_GATEWAY.download_response(download_id)
    return {
        "status": "success",
        "data": res
    }


def post_anaf_vat_check_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/anaf/vat-registry/check requests."""
    cif = payload.get("cif", "")
    info = ANAF_GATEWAY.check_vat_registry(cif)

    return {
        "status": "success",
        "cif": info.cif,
        "company_name": info.name,
        "address": info.address,
        "vat_registered": info.vat_registered,
        "vat_start_date": info.vat_start_date,
        "vat_split_active": info.vat_split_active,
        "tvai_active": info.tvai_active,
        "inactivated": info.inactivated,
        "message": info.status_msg
    }


def get_anaf_invoices_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handles GET /api/v1/anaf/invoices requests."""
    status_filter = params.get("status")
    result_list = []

    for inv_id, inv in _STORED_INVOICES.items():
        if status_filter and inv.status.value != status_filter:
            continue
        result_list.append({
            "invoice_id": inv.invoice_id,
            "series": inv.series,
            "number": inv.number,
            "supplier_cif": inv.supplier.formatted_cif(),
            "customer_cif": inv.customer.formatted_cif(),
            "issue_date": inv.issue_date,
            "currency": inv.currency,
            "total_payable": inv.total_payable_amount,
            "status": inv.status.value,
            "upload_id": inv.upload_id,
            "download_id": inv.download_id,
            "audit_hash": inv.audit_hash
        })

    return {
        "status": "success",
        "total": len(result_list),
        "invoices": result_list
    }
