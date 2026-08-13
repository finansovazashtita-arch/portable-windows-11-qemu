"""
M79 Poland KSeF e-Fakturowanie REST API Router & Handlers.
(REST API Рутер и хендлъри за KSeF и GUS BIR проверки)

Exposes RESTful API endpoints for:
- Gateway health & session checking (/api/v1/ksef/health)
- Session Token & Challenge authentication (/api/v1/ksef/auth/session)
- FA(2)/FA(3) XML invoice generation (/api/v1/ksef/invoices/generate-xml)
- Invoice submission upload (/api/v1/ksef/invoices/submit)
- Processing status tracking (/api/v1/ksef/invoices/status/{reference_number})
- UPO receipt XML download (/api/v1/ksef/invoices/upo/{ksef_number})
- GUS BIR real-time company verification (/api/v1/ksef/gus/check)
- NIP check-digit validation (/api/v1/ksef/nip/validate)
- Query stored invoices (/api/v1/ksef/invoices)
"""

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.integration.ksef_gateway import (
    KSeFEInvoiceGateway,
    KSeFInvoice,
    KSeFParty,
    KSeFInvoiceItem,
    KSeFInvoiceType,
    KSeFSchemaVersion,
    KSeFInvoiceStatus,
    KSeFVATCategory,
    KSeFEnvironment,
    validate_nip
)
from src.integration.gus_bir_api import GUSBIRClient, GUSCompanyData

logger = logging.getLogger("ksef_api")

# Global KSeF Gateway & GUS Client Instances
KSEF_GATEWAY = KSeFEInvoiceGateway(environment=KSeFEnvironment.TEST)
GUS_CLIENT = GUSBIRClient()


def _parse_party(party_dict: Dict[str, Any], default_country: str = "PL") -> KSeFParty:
    """Helper to convert JSON dictionary to KSeFParty."""
    return KSeFParty(
        nip=party_dict.get("nip", "5260250274"),
        name=party_dict.get("name", "Polskie Przedsiębiorstwo Sp. z o.o."),
        trade_register_no=party_dict.get("trade_register_no", party_dict.get("krs", "")),
        street=party_dict.get("street", "ul. Marszałkowska"),
        building_no=party_dict.get("building_no", "100"),
        flat_no=party_dict.get("flat_no", ""),
        city=party_dict.get("city", "Warszawa"),
        postal_code=party_dict.get("postal_code", "00-001"),
        country_code=party_dict.get("country_code", default_country),
        regon=party_dict.get("regon", ""),
        krs=party_dict.get("krs", ""),
        email=party_dict.get("email", ""),
        phone=party_dict.get("phone", ""),
        iban=party_dict.get("iban", ""),
        bank_name=party_dict.get("bank_name", ""),
        vat_registered=party_dict.get("vat_registered", True)
    )


def _parse_invoice_items(items_list: List[Dict[str, Any]]) -> List[KSeFInvoiceItem]:
    """Helper to convert JSON array to KSeFInvoiceItem list."""
    res = []
    for idx, item in enumerate(items_list, start=1):
        vat_cat_str = str(item.get("vat_category", "23"))
        try:
            vat_cat = KSeFVATCategory(vat_cat_str)
        except ValueError:
            vat_cat = KSeFVATCategory.STANDARD

        res.append(KSeFInvoiceItem(
            line_id=str(item.get("line_id", idx)),
            description=item.get("description", f"Towar / Usługa {idx}"),
            quantity=float(item.get("quantity", 1.0)),
            unit_of_measure=item.get("unit_of_measure", "szt"),
            unit_price=float(item.get("unit_price", 0.0)),
            net_amount=float(item.get("net_amount", 0.0)),
            vat_rate=float(item.get("vat_rate", 23.0)),
            vat_category=vat_cat,
            vat_amount=float(item.get("vat_amount", 0.0)),
            gross_amount=float(item.get("gross_amount", 0.0)),
            gtu_code=item.get("gtu_code", ""),
            pkwiu_code=item.get("pkwiu_code", "")
        ))
    return res


def _parse_invoice_payload(payload: Dict[str, Any]) -> KSeFInvoice:
    """Helper to convert JSON payload into KSeFInvoice object."""
    supp_dict = payload.get("supplier", {})
    cust_dict = payload.get("customer", {})

    supplier = _parse_party(supp_dict, "PL")
    customer = _parse_party(cust_dict, "PL")
    items = _parse_invoice_items(payload.get("items", []))

    inv_type_str = payload.get("invoice_type", "VAT")
    try:
        inv_type = KSeFInvoiceType(inv_type_str)
    except ValueError:
        inv_type = KSeFInvoiceType.VAT

    schema_ver_str = payload.get("schema_version", "FA(2)")
    try:
        schema_version = KSeFSchemaVersion(schema_ver_str)
    except ValueError:
        schema_version = KSeFSchemaVersion.FA_2

    return KSeFInvoice(
        invoice_id=payload.get("invoice_id", f"FV/2026/08/{int(datetime.now(timezone.utc).timestamp())}"),
        issue_date=payload.get("issue_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        sale_date=payload.get("sale_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        supplier=supplier,
        customer=customer,
        items=items,
        invoice_type=inv_type,
        schema_version=schema_version,
        currency=payload.get("currency", "PLN"),
        payment_type=payload.get("payment_type", "PRZELEW"),
        payment_due_date=payload.get("payment_due_date", "")
    )


# --- ROUTER FUNCTIONS ---

def get_ksef_health_handler(params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    session_active = bool(KSEF_GATEWAY.active_session and KSEF_GATEWAY.active_session.is_valid())
    return {
        "status": "UP",
        "gateway": "Poland KSeF Gateway M79",
        "environment": KSEF_GATEWAY.environment.value,
        "session_active": session_active,
        "session_nip": KSEF_GATEWAY.active_session.nip if session_active else None,
        "session_reference": KSEF_GATEWAY.active_session.reference_number if session_active else None,
        "supported_schemas": ["FA(2)", "FA(3)"],
        "gus_service": "CONNECTED",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def post_ksef_auth_session_handler(body: Dict[str, Any]) -> Dict[str, Any]:
    nip = body.get("nip", "5260250274")
    token_key = body.get("token_key", "TEST_TOKEN_123456789")
    env_str = body.get("environment", "TEST")

    try:
        env = KSeFEnvironment(env_str.upper())
        KSEF_GATEWAY.environment = env
    except ValueError:
        pass

    session = KSEF_GATEWAY.authenticate(nip, token_key)
    return {
        "success": True,
        "session_token": session.token,
        "reference_number": session.reference_number,
        "challenge": session.challenge,
        "nip": session.nip,
        "environment": session.environment.value,
        "expires_at": datetime.fromtimestamp(session.expires_at, tz=timezone.utc).isoformat()
    }


def post_ksef_generate_xml_handler(body: Dict[str, Any]) -> Dict[str, Any]:
    invoice = _parse_invoice_payload(body)
    xml_content = KSEF_GATEWAY.generate_invoice_xml(invoice)
    is_valid, errors = KSEF_GATEWAY.validate_invoice(invoice)

    return {
        "success": is_valid,
        "invoice_id": invoice.invoice_id,
        "schema_version": invoice.schema_version.value,
        "net_total": invoice.net_total,
        "vat_total": invoice.vat_total,
        "gross_total": invoice.gross_total,
        "xml": xml_content,
        "validation_errors": errors
    }


def post_ksef_submit_handler(body: Dict[str, Any]) -> Dict[str, Any]:
    invoice = _parse_invoice_payload(body)
    try:
        ksef_ref = KSEF_GATEWAY.submit_invoice(invoice)
        return {
            "success": True,
            "invoice_id": invoice.invoice_id,
            "ksef_reference_number": ksef_ref,
            "upo_number": invoice.upo_number,
            "status": invoice.status.value,
            "net_total": invoice.net_total,
            "vat_total": invoice.vat_total,
            "gross_total": invoice.gross_total,
            "timestamp": invoice.updated_at
        }
    except Exception as e:
        return {
            "success": False,
            "invoice_id": invoice.invoice_id,
            "error": str(e)
        }


def get_ksef_status_handler(reference_number: str) -> Dict[str, Any]:
    return KSEF_GATEWAY.check_status(reference_number)


def get_ksef_upo_handler(ksef_number: str) -> Dict[str, Any]:
    upo_xml = KSEF_GATEWAY.download_upo(ksef_number)
    return {
        "ksef_number": ksef_number,
        "upo_xml": upo_xml
    }


def post_ksef_gus_check_handler(body: Dict[str, Any]) -> Dict[str, Any]:
    nip = body.get("nip", "")
    regon = body.get("regon", "")

    try:
        if nip:
            data = GUS_CLIENT.search_by_nip(nip)
        elif regon:
            data = GUS_CLIENT.search_by_regon(regon)
        else:
            return {"success": False, "error": "Must provide either 'nip' or 'regon'"}

        return {
            "success": True,
            "company": {
                "nip": data.nip,
                "regon": data.regon,
                "krs": data.krs,
                "name": data.name,
                "legal_form": data.legal_form,
                "address": data.full_address(),
                "city": data.city,
                "postal_code": data.postal_code,
                "street": data.street,
                "building_no": data.building_no,
                "flat_no": data.flat_no,
                "active": data.active,
                "vat_status": data.vat_status,
                "pkd_codes": data.pkd_codes
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def post_ksef_validate_nip_handler(body: Dict[str, Any]) -> Dict[str, Any]:
    nip = body.get("nip", "")
    is_valid = validate_nip(nip)
    return {
        "nip": nip,
        "is_valid": is_valid
    }


def get_ksef_invoices_handler(params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    invoices = KSEF_GATEWAY.list_invoices()
    res = []
    for inv in invoices:
        res.append({
            "invoice_id": inv.invoice_id,
            "issue_date": inv.issue_date,
            "supplier_name": inv.supplier.name,
            "supplier_nip": inv.supplier.clean_nip(),
            "customer_name": inv.customer.name,
            "customer_nip": inv.customer.clean_nip(),
            "gross_total": inv.gross_total,
            "ksef_reference_number": inv.ksef_reference_number,
            "status": inv.status.value,
            "schema_version": inv.schema_version.value
        })
    return {
        "count": len(res),
        "invoices": res
    }
