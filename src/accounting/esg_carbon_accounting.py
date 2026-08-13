"""
Enterprise ESG & Carbon Tax Accounting Engine (M81).

Implements:
1. GHG Protocol (Scope 1, Scope 2 Location/Market, and Scope 3) Carbon Footprint Calculation.
2. EU CBAM (Carbon Border Adjustment Mechanism) embedded emissions & carbon tax liability calculations.
3. Bulgarian Statutory Double-Entry Accounting Generator:
   - Debit Account 609 ("Други разходи / Разходи за въглеродни провизии")
   - Credit Account 454 ("Разчети за въглеродни данъци и CBAM квоти")
4. CSRD (Corporate Sustainability Reporting Directive) / ESRS E1 Climate Change Report Exporter.
"""

import dataclasses
from enum import Enum
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("esg_carbon_accounting")

# Fixed EUR to BGN currency exchange rate (Bulgarian Lev Peg)
EUR_TO_BGN_RATE = 1.95583

# Default EU Member State Country Codes (Exempt from CBAM import carbon taxes)
EU_MEMBER_STATES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
    "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",
}


class GHGScope(str, Enum):
    """GHG Protocol Scope classification."""
    SCOPE_1 = "Scope 1 (Direct Emissions)"
    SCOPE_2_LOCATION = "Scope 2 (Indirect - Grid Location-Based)"
    SCOPE_2_MARKET = "Scope 2 (Indirect - Market-Based Tariff)"
    SCOPE_3 = "Scope 3 (Value Chain - Purchased Goods & Services)"


class CBAMCategory(str, Enum):
    """EU CBAM Covered Sector Goods Categories."""
    STEEL = "Steel & Iron Products"
    ALUMINUM = "Aluminum Products"
    CEMENT = "Cement & Clinker"
    FERTILIZERS = "Fertilizers & Ammonia"
    HYDROGEN = "Hydrogen"
    ELECTRICITY = "Electricity Import"
    NOT_APPLICABLE = "Not Applicable"


# Default DEFRA / IEA / EU ETS Emission Factors (in kgCO2e or tCO2e per primary unit)
DEFAULT_EMISSION_FACTORS: Dict[str, Dict[str, Any]] = {
    # Scope 1 - Direct Fuels
    "diesel_fuel": {
        "scope": GHGScope.SCOPE_1,
        "unit": "liter",
        "factor_kg_co2e": 2.687,  # kg CO2e per liter diesel
        "description": "Автомобилен дизел (Scope 1)",
    },
    "petrol_gasoline": {
        "scope": GHGScope.SCOPE_1,
        "unit": "liter",
        "factor_kg_co2e": 2.314,  # kg CO2e per liter petrol
        "description": "Автомобилен бензин (Scope 1)",
    },
    "natural_gas": {
        "scope": GHGScope.SCOPE_1,
        "unit": "m3",
        "factor_kg_co2e": 2.020,  # kg CO2e per m3 natural gas
        "description": "Природен газ за отопление/промишленост (Scope 1)",
    },
    "lpg": {
        "scope": GHGScope.SCOPE_1,
        "unit": "liter",
        "factor_kg_co2e": 1.557,  # kg CO2e per liter LPG
        "description": "Пропан-бутан / LPG (Scope 1)",
    },
    "heavy_fuel_oil": {
        "scope": GHGScope.SCOPE_1,
        "unit": "kg",
        "factor_kg_co2e": 3.178,
        "description": "Мазут / Промишлено гориво (Scope 1)",
    },

    # Scope 2 - Electricity & Heating
    "electricity_grid_bg": {
        "scope": GHGScope.SCOPE_2_LOCATION,
        "unit": "kWh",
        "factor_kg_co2e": 0.420,  # kg CO2e per kWh BG Electricity Grid Mix
        "description": "Електроенергия от мрежата в България (Scope 2 Location-Based)",
    },
    "electricity_green_tariff": {
        "scope": GHGScope.SCOPE_2_MARKET,
        "unit": "kWh",
        "factor_kg_co2e": 0.015,  # kg CO2e per kWh 100% Renewable Tariff (GO/Guarantee of Origin)
        "description": "Зелена електроенергия с ВЕИ сертификат (Scope 2 Market-Based)",
    },
    "district_heating": {
        "scope": GHGScope.SCOPE_2_LOCATION,
        "unit": "kWh",
        "factor_kg_co2e": 0.280,
        "description": "Топлофикация / Промишлена пара (Scope 2)",
    },

    # Scope 3 & CBAM Goods
    "imported_steel": {
        "scope": GHGScope.SCOPE_3,
        "unit": "ton",
        "factor_t_co2e": 1.850,  # tCO2e per metric ton steel
        "cbam_category": CBAMCategory.STEEL,
        "is_cbam": True,
        "description": "Вносна стомана и стоманени профили (CBAM)",
    },
    "imported_aluminum": {
        "scope": GHGScope.SCOPE_3,
        "unit": "ton",
        "factor_t_co2e": 4.500,  # tCO2e per metric ton aluminum
        "cbam_category": CBAMCategory.ALUMINUM,
        "is_cbam": True,
        "description": "Вносен алуминий (CBAM)",
    },
    "imported_cement": {
        "scope": GHGScope.SCOPE_3,
        "unit": "ton",
        "factor_t_co2e": 0.820,  # tCO2e per metric ton cement
        "cbam_category": CBAMCategory.CEMENT,
        "is_cbam": True,
        "description": "Вносен цимент и клинкер (CBAM)",
    },
    "imported_fertilizer": {
        "scope": GHGScope.SCOPE_3,
        "unit": "ton",
        "factor_t_co2e": 2.100,  # tCO2e per metric ton nitrogen fertilizer
        "cbam_category": CBAMCategory.FERTILIZERS,
        "is_cbam": True,
        "description": "Вносни азотни торове и амоняк (CBAM)",
    },
    "air_travel_passenger": {
        "scope": GHGScope.SCOPE_3,
        "unit": "passenger_km",
        "factor_kg_co2e": 0.158,
        "description": "Служебни самолетни полети (Scope 3 Category 6)",
    },
    "freight_transport_road": {
        "scope": GHGScope.SCOPE_3,
        "unit": "ton_km",
        "factor_kg_co2e": 0.105,
        "description": "Автомобилен товарни транспорт (Scope 3 Category 4)",
    },
    "purchased_paper_cardboard": {
        "scope": GHGScope.SCOPE_3,
        "unit": "kg",
        "factor_kg_co2e": 0.920,
        "description": "Закупена хартия и опаковки (Scope 3 Category 1)",
    },
}


@dataclasses.dataclass
class PurchaseInvoiceItem:
    """Represents a purchase invoice ledger item subject to carbon accounting / CBAM."""
    item_id: str
    document_number: str
    date: str
    description: str
    quantity: float
    unit: str  # e.g., "kWh", "MWh", "liter", "m3", "kg", "ton", "passenger_km", "ton_km"
    activity_type: str  # Matches keys in DEFAULT_EMISSION_FACTORS or custom
    amount_eur: float
    origin_country: str = "BG"  # 2-letter ISO country code
    cn_code: Optional[str] = None  # Combined Nomenclature HS Code for CBAM items
    custom_emission_factor_kg_co2e: Optional[float] = None
    carbon_price_paid_in_origin_eur: float = 0.0  # Foreign carbon tax credit for CBAM


@dataclasses.dataclass
class EmissionsCalculationResult:
    """Calculated carbon footprint metrics for an individual purchase invoice line item."""
    item_id: str
    document_number: str
    activity_type: str
    description: str
    quantity: float
    unit: str
    scope: str
    emission_factor_used: float  # in kgCO2e / unit (or converted)
    tco2e: float  # Metric tons of CO2 equivalent
    is_cbam_applicable: bool
    cbam_category: str
    origin_country: str
    cbam_embedded_tco2e: float
    cbam_effective_carbon_price_eur: float
    cbam_tax_liability_eur: float
    cbam_tax_liability_bgn: float


@dataclasses.dataclass
class CarbonFootprintSummary:
    """Aggregated organization-wide carbon footprint and CBAM tax summary."""
    reporting_period: str
    total_invoice_items: int
    scope1_tco2e: float
    scope2_location_tco2e: float
    scope2_market_tco2e: float
    scope3_tco2e: float
    total_tco2e: float
    cbam_total_embedded_tco2e: float
    cbam_total_tax_liability_eur: float
    cbam_total_tax_liability_bgn: float
    revenue_eur: float
    carbon_intensity_tco2e_per_k_eur: float
    itemized_results: List[EmissionsCalculationResult]


@dataclasses.dataclass
class CarbonJournalEntry:
    """Statutory Bulgarian double-entry accounting entry for carbon tax provisions."""
    date: str
    document_number: str
    narrative: str
    debit_account: str  # Account 609 ("Други разходи")
    debit_name: str
    credit_account: str  # Account 454 ("Разчети за въглеродни данъци и CBAM квоти")
    credit_name: str
    amount_bgn: float
    amount_eur: float
    tco2e_volume: float
    scope_breakdown: Dict[str, float]


@dataclasses.dataclass
class CSRDReport:
    """CSRD ESRS E1 Climate Change compliance report payload."""
    reporting_period: str
    organization_name: str
    esrs_standard: str
    scope1_direct_tco2e: float
    scope2_indirect_location_tco2e: float
    scope2_indirect_market_tco2e: float
    scope3_value_chain_tco2e: float
    total_ghg_emissions_tco2e: float
    cbam_imported_embedded_emissions_tco2e: float
    cbam_tax_liability_eur: float
    cbam_tax_liability_bgn: float
    carbon_journal_provisions_posted_bgn: float
    carbon_intensity_tco2e_per_k_eur: float
    compliance_status: str
    recommendations: List[str]


class ESGCarbonAccountingEngine:
    """Core Engine for GHG Carbon Footprint, EU CBAM Taxes & Double-Entry Accounting."""

    def __init__(
        self,
        default_carbon_price_eur: float = 85.0,
        emission_factors: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.default_carbon_price_eur = default_carbon_price_eur
        self.emission_factors = emission_factors or DEFAULT_EMISSION_FACTORS

    def calculate_item_emissions(
        self,
        item: PurchaseInvoiceItem,
        carbon_price_eur: Optional[float] = None,
    ) -> EmissionsCalculationResult:
        """Calculates carbon footprint (tCO2e) and CBAM taxes for a single invoice item."""
        effective_carbon_price = carbon_price_eur if carbon_price_eur is not None else self.default_carbon_price_eur
        factor_info = self.emission_factors.get(item.activity_type, {})

        scope = factor_info.get("scope", GHGScope.SCOPE_3).value if isinstance(factor_info.get("scope"), GHGScope) else str(factor_info.get("scope", GHGScope.SCOPE_3))
        
        # Determine emission factor (kgCO2e per unit or tCO2e per unit)
        if item.custom_emission_factor_kg_co2e is not None:
            ef_kg = item.custom_emission_factor_kg_co2e
        elif "factor_t_co2e" in factor_info:
            ef_kg = factor_info["factor_t_co2e"] * 1000.0
        else:
            ef_kg = factor_info.get("factor_kg_co2e", 0.0)

        # Normalize units if necessary (e.g. MWh -> 1000 kWh, ton -> 1000 kg)
        qty = item.quantity
        normalized_qty = qty
        unit_lower = item.unit.lower()

        if unit_lower == "mwh":
            normalized_qty = qty * 1000.0  # converted to kWh
        elif unit_lower == "gwh":
            normalized_qty = qty * 1000000.0

        # Calculate metric tons of CO2 equivalent (tCO2e)
        total_kg_co2e = normalized_qty * ef_kg
        tco2e = round(total_kg_co2e / 1000.0, 4)

        # Determine CBAM Applicability
        origin = item.origin_country.upper().strip()
        is_non_eu = origin not in EU_MEMBER_STATES
        is_cbam_factor = factor_info.get("is_cbam", False) or item.cn_code is not None
        is_cbam_applicable = is_non_eu and is_cbam_factor

        cbam_cat = factor_info.get("cbam_category", CBAMCategory.NOT_APPLICABLE)
        cbam_category_str = cbam_cat.value if isinstance(cbam_cat, CBAMCategory) else str(cbam_cat)

        cbam_embedded_tco2e = 0.0
        cbam_tax_liability_eur = 0.0
        cbam_tax_liability_bgn = 0.0

        if is_cbam_applicable:
            cbam_embedded_tco2e = tco2e
            # Gross CBAM tax = embedded emissions * EU ETS carbon price
            gross_tax_eur = cbam_embedded_tco2e * effective_carbon_price
            # Deduct foreign carbon tax credit paid in country of origin
            net_tax_eur = max(0.0, gross_tax_eur - item.carbon_price_paid_in_origin_eur)
            cbam_tax_liability_eur = round(net_tax_eur, 2)
            cbam_tax_liability_bgn = round(cbam_tax_liability_eur * EUR_TO_BGN_RATE, 2)

        return EmissionsCalculationResult(
            item_id=item.item_id,
            document_number=item.document_number,
            activity_type=item.activity_type,
            description=item.description,
            quantity=qty,
            unit=item.unit,
            scope=scope,
            emission_factor_used=ef_kg,
            tco2e=tco2e,
            is_cbam_applicable=is_cbam_applicable,
            cbam_category=cbam_category_str,
            origin_country=origin,
            cbam_embedded_tco2e=cbam_embedded_tco2e,
            cbam_effective_carbon_price_eur=effective_carbon_price if is_cbam_applicable else 0.0,
            cbam_tax_liability_eur=cbam_tax_liability_eur,
            cbam_tax_liability_bgn=cbam_tax_liability_bgn,
        )

    def calculate_footprint(
        self,
        items: List[PurchaseInvoiceItem],
        period: str = "2026-Q3",
        revenue_eur: float = 0.0,
        carbon_price_eur: Optional[float] = None,
    ) -> CarbonFootprintSummary:
        """Calculates aggregated Scope 1-3 carbon footprint and total CBAM tax liability."""
        results: List[EmissionsCalculationResult] = []
        scope1_sum = 0.0
        scope2_loc_sum = 0.0
        scope2_mkt_sum = 0.0
        scope3_sum = 0.0
        cbam_embedded_sum = 0.0
        cbam_tax_eur_sum = 0.0

        for item in items:
            res = self.calculate_item_emissions(item, carbon_price_eur=carbon_price_eur)
            results.append(res)

            if "Scope 1" in res.scope:
                scope1_sum += res.tco2e
            elif "Location-Based" in res.scope:
                scope2_loc_sum += res.tco2e
            elif "Market-Based" in res.scope:
                scope2_mkt_sum += res.tco2e
            else:
                scope3_sum += res.tco2e

            if res.is_cbam_applicable:
                cbam_embedded_sum += res.cbam_embedded_tco2e
                cbam_tax_eur_sum += res.cbam_tax_liability_eur

        scope1_sum = round(scope1_sum, 4)
        scope2_loc_sum = round(scope2_loc_sum, 4)
        scope2_mkt_sum = round(scope2_mkt_sum, 4)
        scope3_sum = round(scope3_sum, 4)
        total_tco2e = round(scope1_sum + scope2_loc_sum + scope3_sum, 4)

        cbam_embedded_sum = round(cbam_embedded_sum, 4)
        cbam_tax_eur_sum = round(cbam_tax_eur_sum, 2)
        cbam_tax_bgn_sum = round(cbam_tax_eur_sum * EUR_TO_BGN_RATE, 2)

        # Intensity metric: tCO2e per €1000 revenue
        intensity = 0.0
        if revenue_eur > 0:
            intensity = round((total_tco2e / (revenue_eur / 1000.0)), 4)

        return CarbonFootprintSummary(
            reporting_period=period,
            total_invoice_items=len(items),
            scope1_tco2e=scope1_sum,
            scope2_location_tco2e=scope2_loc_sum,
            scope2_market_tco2e=scope2_mkt_sum,
            scope3_tco2e=scope3_sum,
            total_tco2e=total_tco2e,
            cbam_total_embedded_tco2e=cbam_embedded_sum,
            cbam_total_tax_liability_eur=cbam_tax_eur_sum,
            cbam_total_tax_liability_bgn=cbam_tax_bgn_sum,
            revenue_eur=revenue_eur,
            carbon_intensity_tco2e_per_k_eur=intensity,
            itemized_results=results,
        )

    def generate_carbon_tax_journals(
        self,
        summary: CarbonFootprintSummary,
        doc_number: str = "CBAM-PROV-2026-001",
        date_str: str = "2026-08-31",
    ) -> List[CarbonJournalEntry]:
        """
        Generates statutory Bulgarian double-entry journal entries for carbon provisions:
        Debit 609 ("Други разходи") / Credit 454 ("Разчети за въглеродни данъци и CBAM квоти").
        """
        entries: List[CarbonJournalEntry] = []

        # 1. CBAM Import Carbon Tax Provision Entry (Account 609 / Account 454)
        if summary.cbam_total_tax_liability_bgn > 0:
            entries.append(
                CarbonJournalEntry(
                    date=date_str,
                    document_number=doc_number,
                    narrative=f"Начислена въглеродна провизия / CBAM данък за периода {summary.reporting_period} (Общо {summary.cbam_total_embedded_tco2e} tCO2e)",
                    debit_account="609",
                    debit_name="Други разходи - Разходи за въглеродни провизии и CBAM квоти",
                    credit_account="454",
                    credit_name="Разчети за въглеродни данъци и CBAM сертификати",
                    amount_bgn=summary.cbam_total_tax_liability_bgn,
                    amount_eur=summary.cbam_total_tax_liability_eur,
                    tco2e_volume=summary.cbam_total_embedded_tco2e,
                    scope_breakdown={
                        "Scope 1": summary.scope1_tco2e,
                        "Scope 2": summary.scope2_location_tco2e,
                        "Scope 3 / CBAM": summary.cbam_total_embedded_tco2e,
                    },
                )
            )

        # 2. General Scope 1 & 2 Carbon Tax Shadow Provision (if applicable/configured)
        elif summary.total_tco2e > 0:
            # Shadow carbon price provision for internal carbon pricing
            shadow_tax_eur = round(summary.total_tco2e * 25.0, 2)  # internal shadow price €25/ton
            shadow_tax_bgn = round(shadow_tax_eur * EUR_TO_BGN_RATE, 2)

            entries.append(
                CarbonJournalEntry(
                    date=date_str,
                    document_number=f"INT-CARBON-{doc_number}",
                    narrative=f"Вътрешна въглеродна провизия за Scope 1-3 за периода {summary.reporting_period} ({summary.total_tco2e} tCO2e)",
                    debit_account="609",
                    debit_name="Други разходи - Вътрешни въглеродни квоти",
                    credit_account="454",
                    credit_name="Разчети за въглеродни данъци",
                    amount_bgn=shadow_tax_bgn,
                    amount_eur=shadow_tax_eur,
                    tco2e_volume=summary.total_tco2e,
                    scope_breakdown={
                        "Scope 1": summary.scope1_tco2e,
                        "Scope 2": summary.scope2_location_tco2e,
                        "Scope 3": summary.scope3_tco2e,
                    },
                )
            )

        return entries

    def generate_csrd_report(
        self,
        summary: CarbonFootprintSummary,
        organization_name: str = "Enterprise ESG Corp EAD",
    ) -> CSRDReport:
        """Generates a Corporate Sustainability Reporting Directive (CSRD) ESRS E1 Report."""
        posted_bgn = summary.cbam_total_tax_liability_bgn

        recommendations = []
        if summary.scope2_location_tco2e > 10.0:
            recommendations.append("Преминаване към 100% зелена електроенергия с ВЕИ сертификати (GO) за намаляване на Scope 2 емисиите.")
        if summary.cbam_total_tax_liability_eur > 1000.0:
            recommendations.append("Оптимизиране на доставките на стомана/алуминий от нисковъглеродни производители за намаляване на CBAM данъците.")
        if summary.scope1_tco2e > 20.0:
            recommendations.append("Електрификация на автопарка и подмяна на дизеловите агрегати за намаляване на Scope 1 емисиите.")

        if not recommendations:
            recommendations.append("Отлична въглеродна ефективност. Продължете мониторинга на Scope 1-3 емисиите.")

        status = "COMPLIANT_ESRS_E1" if summary.total_invoice_items > 0 else "NO_DATA"

        return CSRDReport(
            reporting_period=summary.reporting_period,
            organization_name=organization_name,
            esrs_standard="ESRS E1 Climate Change Standard (EU CSRD)",
            scope1_direct_tco2e=summary.scope1_tco2e,
            scope2_indirect_location_tco2e=summary.scope2_location_tco2e,
            scope2_indirect_market_tco2e=summary.scope2_market_tco2e,
            scope3_value_chain_tco2e=summary.scope3_tco2e,
            total_ghg_emissions_tco2e=summary.total_tco2e,
            cbam_imported_embedded_emissions_tco2e=summary.cbam_total_embedded_tco2e,
            cbam_tax_liability_eur=summary.cbam_total_tax_liability_eur,
            cbam_tax_liability_bgn=summary.cbam_total_tax_liability_bgn,
            carbon_journal_provisions_posted_bgn=posted_bgn,
            carbon_intensity_tco2e_per_k_eur=summary.carbon_intensity_tco2e_per_k_eur,
            compliance_status=status,
            recommendations=recommendations,
        )
