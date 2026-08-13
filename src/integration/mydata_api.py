"""
M80 Greece myDATA (AADE) REST API Router & Handlers.

Exposes RESTful endpoints for:
  GET  /api/v1/mydata/health              — Gateway health & configuration status
  POST /api/v1/mydata/afm/validate        — Greek AFM (ΑΦΜ) validation
  POST /api/v1/mydata/invoices/generate-xml  — Build myDATA XML document
  POST /api/v1/mydata/invoices/validate   — Business-rule validation (pre-submission)
  POST /api/v1/mydata/send-invoices       — Send income invoices to AADE
  POST /api/v1/mydata/send-expenses       — Send expense classifications to AADE
  GET  /api/v1/mydata/incomes/request     — Query transmitted income documents (RequestMyIncome)
  POST /api/v1/mydata/cancel/{mark}       — Cancel a submitted invoice by MARK
  GET  /api/v1/mydata/marks               — List all registered MARKs
  GET  /api/v1/mydata/marks/{mark}        — Get status of a specific MARK
  POST /api/v1/mydata/journal-entries     — Generate Greek double-entry journal entries for invoice
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.integration.mydata_gateway import (
    GreekParty,
    IncomeClassificationType,
    ExpenseClassificationType,
    IncomeClassificationCategory,
    ExpenseClassificationCategory,
    InvoiceLineItem,
    InvoiceType,
    MyDATAEnvironment,
    MyDATAGateway,
    MyDATAInvoice,
    VATCategory,
    validate_afm,
)

logger = logging.getLogger("mydata_api")

# ---------------------------------------------------------------------------
# Global Gateway Instance
# ---------------------------------------------------------------------------
MYDATA_GATEWAY = MyDATAGateway(
    aade_user_id="DEMO_AADE_USER_ID",
    subscription_key="DEMO_SUBSCRIPTION_KEY",
    environment=MyDATAEnvironment.SANDBOX,
)

_STORED_INVOICES: Dict[str, MyDATAInvoice] = {}


# ---------------------------------------------------------------------------
# HELPER PARSERS
# ---------------------------------------------------------------------------

def _parse_greek_party(d: Dict[str, Any]) -> GreekParty:
    """Converts a JSON dict into a GreekParty dataclass."""
    return GreekParty(
        afm=d.get("afm", "094018881"),
        name=d.get("name", "Εταιρεία Α.Ε."),
        country_code=d.get("country_code", "GR"),
        address=d.get("address", ""),
        city=d.get("city", ""),
        postal_code=d.get("postal_code", ""),
        branch=int(d.get("branch", 0)),
    )


def _parse_line_items(items: List[Dict[str, Any]]) -> List[InvoiceLineItem]:
    """Converts a JSON list of line item dicts into InvoiceLineItem objects."""
    result = []
    for idx, item in enumerate(items, start=1):
        vat_cat_str = str(item.get("vat_category", "1"))
        try:
            vat_cat = VATCategory(vat_cat_str)
        except ValueError:
            vat_cat = VATCategory.RATE_24

        result.append(InvoiceLineItem(
            line_number=int(item.get("line_number", idx)),
            net_value=float(item.get("net_value", 0.0)),
            vat_category=vat_cat,
            vat_amount=float(item.get("vat_amount", 0.0)),
            income_classification_type=item.get("income_classification_type"),
            income_classification_category=item.get("income_classification_category"),
            expense_classification_type=item.get("expense_classification_type"),
            expense_classification_category=item.get("expense_classification_category"),
            quantity=float(item.get("quantity", 1.0)),
            unit_price=float(item.get("unit_price", 0.0)),
            description=item.get("description", ""),
        ))
    return result


def _parse_invoice(payload: Dict[str, Any]) -> MyDATAInvoice:
    """Converts a JSON payload dict into a MyDATAInvoice object."""
    issuer_dict = payload.get("issuer", {})
    counterpart_dict = payload.get("counterpart")

    inv_type_str = payload.get("invoice_type", "1.1")
    try:
        inv_type = InvoiceType(inv_type_str)
    except ValueError:
        inv_type = InvoiceType.SALES_INVOICE

    uid = payload.get("uid") or f"INV-GR-{int(datetime.now(timezone.utc).timestamp())}"

    return MyDATAInvoice(
        uid=uid,
        issuer=_parse_greek_party(issuer_dict),
        invoice_type=inv_type,
        issue_date=payload.get("issue_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        series=payload.get("series", "A"),
        aa=str(payload.get("aa", "1")),
        currency=payload.get("currency", "EUR"),
        counterpart=_parse_greek_party(counterpart_dict) if counterpart_dict else None,
        lines=_parse_line_items(payload.get("lines", [])),
        payment_method=int(payload.get("payment_method", 3)),
        payment_amount=float(payload.get("payment_amount", 0.0)),
        notes=payload.get("notes", ""),
    )


def _parse_invoice_list(payload: Dict[str, Any]) -> List[MyDATAInvoice]:
    """Parses a payload containing a list of invoices or a single invoice."""
    invoices_list = payload.get("invoices")
    if invoices_list and isinstance(invoices_list, list):
        return [_parse_invoice(i) for i in invoices_list]
    # Single invoice payload
    return [_parse_invoice(payload)]


def _invoice_summary(inv: MyDATAInvoice) -> Dict[str, Any]:
    """Returns a compact summary dict for a stored invoice."""
    return {
        "uid": inv.uid,
        "issuer_afm": inv.issuer.clean_afm(),
        "invoice_type": inv.invoice_type.value,
        "issue_date": inv.issue_date,
        "series": inv.series,
        "aa": inv.aa,
        "total_net": inv.total_net_value,
        "total_vat": inv.total_vat_amount,
        "total_gross": inv.total_gross_value,
        "status": inv.status.value,
        "mark": inv.mark,
        "authentication_code": inv.authentication_code,
        "submitted_at": inv.submitted_at,
    }


# ---------------------------------------------------------------------------
# GET HANDLERS
# ---------------------------------------------------------------------------

def get_mydata_health_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handles GET /api/v1/mydata/health."""
    return MYDATA_GATEWAY.get_health_status()


def get_mydata_marks_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handles GET /api/v1/mydata/marks — lists all registered MARKs."""
    records = MYDATA_GATEWAY.get_mark_registry()
    return {
        "status": "success",
        "total": len(records),
        "marks": records,
    }


def get_mydata_mark_status_handler(mark: str) -> Dict[str, Any]:
    """Handles GET /api/v1/mydata/marks/{mark}."""
    return {
        "status": "success",
        "data": MYDATA_GATEWAY.get_mark_status(mark),
    }


def get_mydata_invoices_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handles GET /api/v1/mydata/invoices — lists stored invoices with optional filter."""
    status_filter = params.get("status")
    inv_type_filter = params.get("invoice_type")

    results = []
    for uid, inv in _STORED_INVOICES.items():
        if status_filter and inv.status.value != status_filter.upper():
            continue
        if inv_type_filter and inv.invoice_type.value != inv_type_filter:
            continue
        results.append(_invoice_summary(inv))

    return {
        "status": "success",
        "total": len(results),
        "invoices": results,
    }


def get_mydata_request_income_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handles GET /api/v1/mydata/incomes/request — queries AADE RequestMyIncome."""
    date_from = params.get("date_from", datetime.now(timezone.utc).strftime("%Y-01-01"))
    date_to = params.get("date_to", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    entity_vat = params.get("entity_vat_number")
    counter_vat = params.get("counter_vat_number")
    mark_filter = params.get("mark")

    result = MYDATA_GATEWAY.request_my_income(
        date_from=date_from,
        date_to=date_to,
        entity_vat_number=entity_vat,
        counter_vat_number=counter_vat,
        invoice_mark=mark_filter,
    )
    return {"status": "success", "data": result}


# ---------------------------------------------------------------------------
# POST HANDLERS
# ---------------------------------------------------------------------------

def post_mydata_afm_validate_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/mydata/afm/validate — validates a Greek AFM."""
    afm_input = payload.get("afm", "")
    result = MYDATA_GATEWAY.validate_afm(afm_input)
    return {
        "status": "success",
        **result,
    }


def post_mydata_generate_xml_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/mydata/invoices/generate-xml — generates InvoicesDoc XML."""
    try:
        invoices = _parse_invoice_list(payload)
    except Exception as e:
        return {"status": "error", "error": f"Σφάλμα ανάλυσης payload: {e}"}

    for inv in invoices:
        _STORED_INVOICES[inv.uid] = inv

    try:
        xml_content = MYDATA_GATEWAY.build_invoices_xml(invoices)
    except ValueError as e:
        return {"status": "error", "error": str(e)}

    summaries = [_invoice_summary(inv) for inv in invoices]
    return {
        "status": "success",
        "count": len(invoices),
        "invoices": summaries,
        "xml_content": xml_content,
    }


def post_mydata_validate_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/mydata/invoices/validate — pre-submission validation."""
    try:
        invoices = _parse_invoice_list(payload)
    except Exception as e:
        return {"status": "error", "error": f"Σφάλμα ανάλυσης payload: {e}"}

    all_results = []
    overall_valid = True
    for inv in invoices:
        result = MYDATA_GATEWAY.validate_invoice(inv)
        if not result["valid"]:
            overall_valid = False
        all_results.append({
            "uid": inv.uid,
            "invoice_type": inv.invoice_type.value,
            **result,
        })

    return {
        "status": "success" if overall_valid else "validation_failed",
        "overall_valid": overall_valid,
        "results": all_results,
    }


def post_mydata_send_invoices_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/mydata/send-invoices — transmits income invoices to AADE."""
    try:
        invoices = _parse_invoice_list(payload)
    except Exception as e:
        return {"status": "error", "error": f"Σφάλμα ανάλυσης payload: {e}"}

    for inv in invoices:
        _STORED_INVOICES[inv.uid] = inv

    result = MYDATA_GATEWAY.send_invoices(invoices)

    # Refresh stored copies with MARK data
    for inv in invoices:
        _STORED_INVOICES[inv.uid] = inv

    return {
        "status": "success" if result.get("success") else "error",
        "submitted": result.get("submitted", 0),
        "environment": result.get("environment"),
        "responses": result.get("responses", []),
        "invoices": [_invoice_summary(inv) for inv in invoices],
        "timestamp": result.get("timestamp"),
    }


def post_mydata_send_expenses_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/mydata/send-expenses — transmits expense classifications."""
    try:
        invoices = _parse_invoice_list(payload)
    except Exception as e:
        return {"status": "error", "error": f"Σφάλμα ανάλυσης payload: {e}"}

    for inv in invoices:
        _STORED_INVOICES[inv.uid] = inv

    result = MYDATA_GATEWAY.send_expenses_classification(invoices)

    for inv in invoices:
        _STORED_INVOICES[inv.uid] = inv

    return {
        "status": "success" if result.get("success") else "error",
        "submitted": result.get("submitted", 0),
        "environment": result.get("environment"),
        "responses": result.get("responses", []),
        "invoices": [_invoice_summary(inv) for inv in invoices],
        "timestamp": result.get("timestamp"),
    }


def post_mydata_cancel_handler(mark: str) -> Dict[str, Any]:
    """Handles POST /api/v1/mydata/cancel/{mark} — cancels a submitted invoice."""
    result = MYDATA_GATEWAY.cancel_invoice(mark)

    # Update stored invoice status if found
    for uid, inv in _STORED_INVOICES.items():
        if inv.mark == mark:
            from src.integration.mydata_gateway import DocumentStatus
            inv.status = DocumentStatus.CANCELLED
            break

    return {
        "status": "success" if result.get("success") else "error",
        "data": result,
    }


def post_mydata_journal_entries_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles POST /api/v1/mydata/journal-entries — generates double-entry journals."""
    try:
        invoice = _parse_invoice(payload)
    except Exception as e:
        return {"status": "error", "error": f"Σφάλμα ανάλυσης payload: {e}"}

    # Use stored invoice if UID exists (to include MARK)
    stored = _STORED_INVOICES.get(invoice.uid)
    target_invoice = stored if stored else invoice

    entries = MYDATA_GATEWAY.generate_journal_entries(target_invoice)
    total_debit = round(sum(e["debit"] for e in entries), 2)
    total_credit = round(sum(e["credit"] for e in entries), 2)

    return {
        "status": "success",
        "uid": target_invoice.uid,
        "invoice_type": target_invoice.invoice_type.value,
        "mark": target_invoice.mark,
        "total_gross": target_invoice.total_gross_value,
        "journal_entries": entries,
        "totals": {
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balanced": abs(total_debit - total_credit) < 0.01,
        },
    }
