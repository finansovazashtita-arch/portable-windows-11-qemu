"""
M81 Enterprise ESG & Carbon Tax Accounting REST API Handlers & Router.

Exposes RESTful endpoints for:
  GET / POST /api/v1/esg/health — ESG Engine health & supported emission factors
  GET / POST /api/v1/esg/footprint/calculate — Calculate Scope 1, 2 & 3 tCO2e carbon footprint
  GET / POST /api/v1/esg/cbam/report — Calculate EU CBAM embedded emissions & carbon tax liability
  GET / POST /api/v1/esg/journals/post — Generate double-entry carbon provision journals (Account 609 / 454)
  GET / POST /api/v1/esg/csrd/export — Export CSRD ESRS E1 Climate Change report
"""

import dataclasses
import logging
from typing import Any, Dict, List, Optional

from src.accounting.esg_carbon_accounting import (
    DEFAULT_EMISSION_FACTORS,
    ESGCarbonAccountingEngine,
    PurchaseInvoiceItem,
    CarbonFootprintSummary,
)

logger = logging.getLogger("esg_api")

# Global singleton ESG engine instance
ESG_ENGINE = ESGCarbonAccountingEngine(default_carbon_price_eur=85.0)

# In-memory sample purchase invoice items for quick demo / default calculations
DEMO_PURCHASE_ITEMS: List[PurchaseInvoiceItem] = [
    PurchaseInvoiceItem(
        item_id="INV-2026-001-L1",
        document_number="INV-2026-001",
        date="2026-08-01",
        description="Промишлена електроенергия от мрежата (50 MWh)",
        quantity=50.0,
        unit="MWh",
        activity_type="electricity_grid_bg",
        amount_eur=7500.0,
        origin_country="BG",
    ),
    PurchaseInvoiceItem(
        item_id="INV-2026-002-L1",
        document_number="INV-2026-002",
        date="2026-08-05",
        description="Дизелово гориво за служебни автомобили (2,500 литра)",
        quantity=2500.0,
        unit="liter",
        activity_type="diesel_fuel",
        amount_eur=3250.0,
        origin_country="BG",
    ),
    PurchaseInvoiceItem(
        item_id="INV-2026-003-L1",
        document_number="INV-2026-003",
        date="2026-08-10",
        description="Внос на горещовалцована стомана от Турция (15 тона)",
        quantity=15.0,
        unit="ton",
        activity_type="imported_steel",
        amount_eur=12000.0,
        origin_country="TR",
        cn_code="72081000",
    ),
    PurchaseInvoiceItem(
        item_id="INV-2026-004-L1",
        document_number="INV-2026-004",
        date="2026-08-12",
        description="Внос на алуминиеви профили от Китай (5 тона)",
        quantity=5.0,
        unit="ton",
        activity_type="imported_aluminum",
        amount_eur=11500.0,
        origin_country="CN",
        cn_code="76041010",
    ),
]


def _parse_invoice_items(raw_items: List[Dict[str, Any]]) -> List[PurchaseInvoiceItem]:
    """Converts a list of dicts into PurchaseInvoiceItem objects."""
    parsed: List[PurchaseInvoiceItem] = []
    for idx, item in enumerate(raw_items):
        parsed.append(
            PurchaseInvoiceItem(
                item_id=str(item.get("item_id", f"ITEM-{idx + 1}")),
                document_number=str(item.get("document_number", f"DOC-{idx + 1}")),
                date=str(item.get("date", "2026-08-13")),
                description=str(item.get("description", "Purchase Item")),
                quantity=float(item.get("quantity", 0.0)),
                unit=str(item.get("unit", "units")),
                activity_type=str(item.get("activity_type", "purchased_paper_cardboard")),
                amount_eur=float(item.get("amount_eur", 0.0)),
                origin_country=str(item.get("origin_country", "BG")).strip().upper(),
                cn_code=item.get("cn_code"),
                custom_emission_factor_kg_co2e=item.get("custom_emission_factor_kg_co2e"),
                carbon_price_paid_in_origin_eur=float(item.get("carbon_price_paid_in_origin_eur", 0.0)),
            )
        )
    return parsed


def get_esg_health_handler() -> Dict[str, Any]:
    """Returns ESG Engine status and supported activity emission factors."""
    return {
        "status": "HEALTHY",
        "module": "M81 Enterprise ESG Sustainability & Carbon Tax Accounting Engine",
        "ghg_protocol_scopes_supported": [
            "Scope 1 (Direct Fuels & Emissions)",
            "Scope 2 (Indirect Grid Location-Based & Green Market Tariffs)",
            "Scope 3 (Purchased Goods & CBAM Implemented Materials)",
        ],
        "default_eu_ets_carbon_price_eur": ESG_ENGINE.default_carbon_price_eur,
        "supported_activity_types": list(DEFAULT_EMISSION_FACTORS.keys()),
        "total_emission_factors": len(DEFAULT_EMISSION_FACTORS),
    }


def calculate_footprint_handler(req_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calculates carbon footprint for purchase items.
    Accepts: { "items": [...], "period": "2026-Q3", "revenue_eur": 250000.0, "carbon_price_eur": 85.0 }
    """
    data = req_data or {}
    raw_items = data.get("items", [])
    items = _parse_invoice_items(raw_items) if raw_items else DEMO_PURCHASE_ITEMS

    period = data.get("period", "2026-Q3")
    revenue_eur = float(data.get("revenue_eur", 250000.0))
    carbon_price = float(data.get("carbon_price_eur", ESG_ENGINE.default_carbon_price_eur))

    summary = ESG_ENGINE.calculate_footprint(
        items=items,
        period=period,
        revenue_eur=revenue_eur,
        carbon_price_eur=carbon_price,
    )
    return dataclasses.asdict(summary)


def get_cbam_report_handler(req_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Filters non-EU CBAM covered goods imports and returns embedded emissions + tax liabilities.
    """
    footprint = calculate_footprint_handler(req_data)
    itemized = footprint.get("itemized_results", [])
    cbam_items = [item for item in itemized if item.get("is_cbam_applicable")]

    return {
        "reporting_period": footprint.get("reporting_period"),
        "cbam_total_imported_items": len(cbam_items),
        "cbam_total_embedded_tco2e": footprint.get("cbam_total_embedded_tco2e"),
        "cbam_total_tax_liability_eur": footprint.get("cbam_total_tax_liability_eur"),
        "cbam_total_tax_liability_bgn": footprint.get("cbam_total_tax_liability_bgn"),
        "eu_ets_carbon_price_per_tco2e_eur": req_data.get("carbon_price_eur", 85.0) if req_data else 85.0,
        "cbam_imported_goods": cbam_items,
    }


def post_carbon_journals_handler(req_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generates double-entry accounting journal entries for carbon provisions (Account 609 / Account 454).
    """
    data = req_data or {}
    footprint_dict = calculate_footprint_handler(data)
    items = _parse_invoice_items(data.get("items", [])) if data.get("items") else DEMO_PURCHASE_ITEMS
    summary = ESG_ENGINE.calculate_footprint(
        items=items,
        period=data.get("period", "2026-Q3"),
        revenue_eur=float(data.get("revenue_eur", 250000.0)),
        carbon_price_eur=float(data.get("carbon_price_eur", ESG_ENGINE.default_carbon_price_eur)),
    )

    doc_number = data.get("document_number", "CBAM-PROV-2026-001")
    date_str = data.get("date", "2026-08-31")

    journals = ESG_ENGINE.generate_carbon_tax_journals(
        summary=summary,
        doc_number=doc_number,
        date_str=date_str,
    )

    journal_dicts = [dataclasses.asdict(j) for j in journals]
    return {
        "status": "SUCCESS",
        "message": f"Генерирани {len(journal_dicts)} двустранни счетоводни операции за въглеродни провизии",
        "journals_posted": journal_dicts,
        "reporting_period": summary.reporting_period,
        "total_provision_bgn": summary.cbam_total_tax_liability_bgn,
        "total_provision_eur": summary.cbam_total_tax_liability_eur,
    }


def export_csrd_report_handler(req_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Exports a CSRD ESRS E1 Climate Change Standard Report payload.
    """
    data = req_data or {}
    items = _parse_invoice_items(data.get("items", [])) if data.get("items") else DEMO_PURCHASE_ITEMS
    summary = ESG_ENGINE.calculate_footprint(
        items=items,
        period=data.get("period", "2026-Q3"),
        revenue_eur=float(data.get("revenue_eur", 250000.0)),
        carbon_price_eur=float(data.get("carbon_price_eur", ESG_ENGINE.default_carbon_price_eur)),
    )

    org_name = data.get("organization_name", "Enterprise ESG Corp EAD")
    report = ESG_ENGINE.generate_csrd_report(summary=summary, organization_name=org_name)

    return dataclasses.asdict(report)
