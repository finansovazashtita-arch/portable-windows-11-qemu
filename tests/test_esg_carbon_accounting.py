"""
Unit and Integration Test Suite for M81 Enterprise ESG & Carbon Tax Accounting Engine.
"""

import json
import os
import tempfile
from typing import Dict, Any
import pytest

from src.accounting.esg_carbon_accounting import (
    DEFAULT_EMISSION_FACTORS,
    EUR_TO_BGN_RATE,
    CBAMCategory,
    CarbonFootprintSummary,
    ESGCarbonAccountingEngine,
    GHGScope,
    PurchaseInvoiceItem,
)
from src.analytics.esg_api import (
    calculate_footprint_handler,
    export_csrd_report_handler,
    get_cbam_report_handler,
    get_esg_health_handler,
    post_carbon_journals_handler,
)
from src.dashboard.dashboard_server import DashboardHandler


class TestESGCarbonAccountingEngine:
    """Unit tests for core ESG carbon accounting engine logic."""

    def test_default_emission_factors_validity(self):
        engine = ESGCarbonAccountingEngine()
        assert "diesel_fuel" in engine.emission_factors
        assert "electricity_grid_bg" in engine.emission_factors
        assert "imported_steel" in engine.emission_factors
        assert len(engine.emission_factors) >= 10

    def test_scope1_diesel_emissions_calculation(self):
        engine = ESGCarbonAccountingEngine()
        item = PurchaseInvoiceItem(
            item_id="1",
            document_number="INV-001",
            date="2026-08-01",
            description="Дизелово гориво",
            quantity=1000.0,  # 1000 liters diesel @ 2.687 kgCO2e/l = 2687 kg = 2.687 tCO2e
            unit="liter",
            activity_type="diesel_fuel",
            amount_eur=1300.0,
            origin_country="BG",
        )

        result = engine.calculate_item_emissions(item)
        assert result.tco2e == 2.687
        assert "Scope 1" in result.scope
        assert not result.is_cbam_applicable
        assert result.cbam_tax_liability_eur == 0.0

    def test_scope1_natural_gas_lpg_heavy_oil(self):
        engine = ESGCarbonAccountingEngine()
        ng_item = PurchaseInvoiceItem("1", "INV-NG", "2026-08-01", "Природен газ", 500.0, "m3", "natural_gas", 400.0, "BG")
        lpg_item = PurchaseInvoiceItem("2", "INV-LPG", "2026-08-01", "LPG", 200.0, "liter", "lpg", 180.0, "BG")
        hfo_item = PurchaseInvoiceItem("3", "INV-HFO", "2026-08-01", "Мазут", 100.0, "kg", "heavy_fuel_oil", 120.0, "BG")

        ng_res = engine.calculate_item_emissions(ng_item)
        lpg_res = engine.calculate_item_emissions(lpg_item)
        hfo_res = engine.calculate_item_emissions(hfo_item)

        assert ng_res.tco2e == round(500.0 * 2.020 / 1000.0, 4)
        assert lpg_res.tco2e == round(200.0 * 1.557 / 1000.0, 4)
        assert hfo_res.tco2e == round(100.0 * 3.178 / 1000.0, 4)

    def test_scope2_electricity_mwh_and_gwh_conversion(self):
        engine = ESGCarbonAccountingEngine()
        item_mwh = PurchaseInvoiceItem(
            item_id="2",
            document_number="INV-002",
            date="2026-08-02",
            description="Електроенергия MWh",
            quantity=10.0,  # 10 MWh = 10,000 kWh @ 0.420 kgCO2e/kWh = 4200 kg = 4.2 tCO2e
            unit="MWh",
            activity_type="electricity_grid_bg",
            amount_eur=1500.0,
            origin_country="BG",
        )
        item_gwh = PurchaseInvoiceItem(
            item_id="2b",
            document_number="INV-002B",
            date="2026-08-02",
            description="Електроенергия GWh",
            quantity=1.0,  # 1 GWh = 1,000,000 kWh @ 0.420 kg = 420 tCO2e
            unit="GWh",
            activity_type="electricity_grid_bg",
            amount_eur=120000.0,
            origin_country="BG",
        )

        res_mwh = engine.calculate_item_emissions(item_mwh)
        res_gwh = engine.calculate_item_emissions(item_gwh)

        assert res_mwh.tco2e == 4.2
        assert res_gwh.tco2e == 420.0

    def test_scope2_market_based_green_tariff(self):
        engine = ESGCarbonAccountingEngine()
        item = PurchaseInvoiceItem(
            item_id="2c",
            document_number="INV-GREEN",
            date="2026-08-02",
            description="Зелена енергия",
            quantity=100.0,
            unit="MWh",
            activity_type="electricity_green_tariff",
            amount_eur=15000.0,
            origin_country="BG",
        )

        res = engine.calculate_item_emissions(item)
        # 100 MWh = 100,000 kWh * 0.015 = 1500 kg = 1.5 tCO2e
        assert res.tco2e == 1.5
        assert "Market-Based" in res.scope

    def test_cbam_non_eu_import_steel_tax_calculation(self):
        engine = ESGCarbonAccountingEngine(default_carbon_price_eur=85.0)
        item = PurchaseInvoiceItem(
            item_id="3",
            document_number="INV-003",
            date="2026-08-05",
            description="Внос на стомана от Турция",
            quantity=20.0,  # 20 tons steel @ 1.85 tCO2e/ton = 37.0 tCO2e
            unit="ton",
            activity_type="imported_steel",
            amount_eur=16000.0,
            origin_country="TR",  # Non-EU triggers CBAM
            cn_code="72081000",
        )

        result = engine.calculate_item_emissions(item)
        assert result.tco2e == 37.0
        assert result.is_cbam_applicable
        assert result.cbam_embedded_tco2e == 37.0
        # Tax = 37.0 * 85.0 = €3,145.00
        assert result.cbam_tax_liability_eur == 3145.0
        assert result.cbam_tax_liability_bgn == round(3145.0 * EUR_TO_BGN_RATE, 2)

    def test_cbam_cement_and_fertilizers(self):
        engine = ESGCarbonAccountingEngine(default_carbon_price_eur=85.0)
        cement_item = PurchaseInvoiceItem("1", "INV-C", "2026-08-01", "Цимент от Египет", 50.0, "ton", "imported_cement", 4000.0, "EG")
        fert_item = PurchaseInvoiceItem("2", "INV-F", "2026-08-01", "Торове от Индия", 10.0, "ton", "imported_fertilizer", 6000.0, "IN")

        c_res = engine.calculate_item_emissions(cement_item)
        f_res = engine.calculate_item_emissions(fert_item)

        assert c_res.is_cbam_applicable
        assert f_res.is_cbam_applicable
        assert c_res.tco2e == round(50.0 * 0.820, 4)
        assert f_res.tco2e == round(10.0 * 2.100, 4)

    def test_eu_member_state_cbam_exemption(self):
        engine = ESGCarbonAccountingEngine()
        item = PurchaseInvoiceItem(
            item_id="4",
            document_number="INV-004",
            date="2026-08-06",
            description="Стомана от Германия",
            quantity=10.0,
            unit="ton",
            activity_type="imported_steel",
            amount_eur=9000.0,
            origin_country="DE",  # Germany is EU member state -> Exempt
        )

        result = engine.calculate_item_emissions(item)
        assert result.tco2e == 18.5
        assert not result.is_cbam_applicable
        assert result.cbam_tax_liability_eur == 0.0

    def test_custom_emission_factor_override(self):
        engine = ESGCarbonAccountingEngine()
        item = PurchaseInvoiceItem(
            item_id="5",
            document_number="INV-CUSTOM",
            date="2026-08-01",
            description="Custom Process Factor",
            quantity=100.0,
            unit="kg",
            activity_type="purchased_paper_cardboard",
            amount_eur=200.0,
            origin_country="BG",
            custom_emission_factor_kg_co2e=5.0,  # 100 kg * 5.0 kgCO2e/kg = 500 kg = 0.5 tCO2e
        )

        res = engine.calculate_item_emissions(item)
        assert res.tco2e == 0.5

    def test_foreign_carbon_tax_deduction(self):
        engine = ESGCarbonAccountingEngine(default_carbon_price_eur=100.0)
        item = PurchaseInvoiceItem(
            item_id="6",
            document_number="INV-005",
            date="2026-08-07",
            description="Внос на алуминий от Великобритания с платен въглероден данък",
            quantity=2.0,  # 2 tons @ 4.5 tCO2e/ton = 9.0 tCO2e. Gross Tax = 9 * 100 = €900
            unit="ton",
            activity_type="imported_aluminum",
            amount_eur=5000.0,
            origin_country="GB",
            carbon_price_paid_in_origin_eur=200.0,  # Paid €200 foreign tax
        )

        result = engine.calculate_item_emissions(item)
        assert result.tco2e == 9.0
        assert result.is_cbam_applicable
        assert result.cbam_tax_liability_eur == 700.0  # 900 - 200 = 700

    def test_aggregated_footprint_summary_and_zero_revenue(self):
        engine = ESGCarbonAccountingEngine()
        items = [
            PurchaseInvoiceItem("1", "INV-1", "2026-08-01", "Дизел", 1000.0, "liter", "diesel_fuel", 1300.0, "BG"),
            PurchaseInvoiceItem("2", "INV-2", "2026-08-02", "Електроенергия", 10.0, "MWh", "electricity_grid_bg", 1500.0, "BG"),
            PurchaseInvoiceItem("3", "INV-3", "2026-08-05", "Стомана ТР", 10.0, "ton", "imported_steel", 8000.0, "TR"),
        ]

        summary = engine.calculate_footprint(items=items, revenue_eur=0.0)
        assert summary.total_invoice_items == 3
        assert summary.scope1_tco2e == 2.687
        assert summary.scope2_location_tco2e == 4.2
        assert summary.scope3_tco2e == 18.5
        assert summary.total_tco2e == round(2.687 + 4.2 + 18.5, 4)
        assert summary.cbam_total_embedded_tco2e == 18.5
        assert summary.cbam_total_tax_liability_eur == 1572.5  # 18.5 * 85
        assert summary.carbon_intensity_tco2e_per_k_eur == 0.0

    def test_double_entry_journal_cbam_provision(self):
        engine = ESGCarbonAccountingEngine()
        items = [
            PurchaseInvoiceItem("1", "INV-1", "2026-08-01", "Внос Стомана", 10.0, "ton", "imported_steel", 8000.0, "TR")
        ]
        summary = engine.calculate_footprint(items)
        journals = engine.generate_carbon_tax_journals(summary, doc_number="CBAM-PROV-001", date_str="2026-08-31")

        assert len(journals) == 1
        entry = journals[0]
        assert entry.debit_account == "609"
        assert entry.credit_account == "454"
        assert entry.amount_bgn > 0.0
        assert entry.amount_bgn == round(entry.amount_eur * EUR_TO_BGN_RATE, 2)
        assert "CBAM" in entry.narrative

    def test_double_entry_journal_internal_shadow_provision(self):
        engine = ESGCarbonAccountingEngine()
        # Non-CBAM items only
        items = [
            PurchaseInvoiceItem("1", "INV-1", "2026-08-01", "Дизел", 1000.0, "liter", "diesel_fuel", 1300.0, "BG")
        ]
        summary = engine.calculate_footprint(items)
        assert summary.cbam_total_tax_liability_bgn == 0.0
        assert summary.total_tco2e > 0.0

        journals = engine.generate_carbon_tax_journals(summary, doc_number="INT-PROV-001")
        assert len(journals) == 1
        entry = journals[0]
        assert entry.debit_account == "609"
        assert entry.credit_account == "454"
        assert entry.amount_eur == round(summary.total_tco2e * 25.0, 2)

    def test_csrd_esrs_e1_report_generation(self):
        engine = ESGCarbonAccountingEngine()
        items = [
            PurchaseInvoiceItem("1", "INV-1", "2026-08-01", "Дизел", 8000.0, "liter", "diesel_fuel", 10400.0, "BG"),
            PurchaseInvoiceItem("2", "INV-2", "2026-08-02", "Електроенергия", 50.0, "MWh", "electricity_grid_bg", 7500.0, "BG"),
            PurchaseInvoiceItem("3", "INV-3", "2026-08-05", "Стомана ТР", 20.0, "ton", "imported_steel", 16000.0, "TR"),
        ]
        summary = engine.calculate_footprint(items, revenue_eur=500000.0)
        csrd = engine.generate_csrd_report(summary, organization_name="Test Enterprise EAD")

        assert csrd.organization_name == "Test Enterprise EAD"
        assert csrd.compliance_status == "COMPLIANT_ESRS_E1"
        assert csrd.total_ghg_emissions_tco2e > 0.0
        assert len(csrd.recommendations) >= 3

    def test_csrd_empty_recommendations(self):
        engine = ESGCarbonAccountingEngine()
        items = []
        summary = engine.calculate_footprint(items)
        csrd = engine.generate_csrd_report(summary)
        assert csrd.compliance_status == "NO_DATA"
        assert "Отлична въглеродна ефективност" in csrd.recommendations[0]


class TestESGAPIEndpoints:
    """Unit tests for ESG API router handlers."""

    def test_esg_health_handler(self):
        health = get_esg_health_handler()
        assert health["status"] == "HEALTHY"
        assert health["total_emission_factors"] > 0

    def test_calculate_footprint_handler_defaults(self):
        res = calculate_footprint_handler()
        assert res["total_invoice_items"] > 0
        assert res["total_tco2e"] > 0.0
        assert "itemized_results" in res

    def test_calculate_footprint_handler_custom_items(self):
        payload = {
            "items": [
                {
                    "item_id": "TEST-1",
                    "document_number": "DOC-99",
                    "quantity": 100.0,
                    "unit": "liter",
                    "activity_type": "diesel_fuel",
                    "amount_eur": 150.0,
                    "origin_country": "BG",
                }
            ],
            "period": "2026-Q3",
            "revenue_eur": 50000.0,
        }
        res = calculate_footprint_handler(payload)
        assert res["total_invoice_items"] == 1
        assert res["scope1_tco2e"] == 0.2687

    def test_get_cbam_report_handler(self):
        res = get_cbam_report_handler()
        assert "cbam_imported_goods" in res
        assert res["cbam_total_imported_items"] >= 0

    def test_post_carbon_journals_handler(self):
        res = post_carbon_journals_handler()
        assert res["status"] == "SUCCESS"
        assert len(res["journals_posted"]) > 0
        assert res["journals_posted"][0]["debit_account"] == "609"
        assert res["journals_posted"][0]["credit_account"] == "454"

    def test_export_csrd_report_handler(self):
        res = export_csrd_report_handler({"organization_name": "Antigravity Audit Corp"})
        assert res["organization_name"] == "Antigravity Audit Corp"
        assert res["esrs_standard"] == "ESRS E1 Climate Change Standard (EU CSRD)"
