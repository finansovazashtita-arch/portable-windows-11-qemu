"""
Unit and Integration Tests for Milestone M72: GFO Generator Engine.
"""

import pytest
import xml.etree.ElementTree as ET
from src.accounting.gfo_generator import (
    CompanyEntityProfile,
    GFOGeneratorEngine,
    GFOReport,
    GFOValidationResult,
)


@pytest.fixture
def sample_company_profile() -> CompanyEntityProfile:
    return CompanyEntityProfile(
        company_name="ТЕСТОВ БИЗНЕС ЕООД",
        eik="123456789",
        address="гр. София, ул. Счетоводна № 10",
        manager_name="Иван Иванов",
        vat_number="BG123456789",
        accounting_standard="NAS",
        economic_activity_code="62.01",
        headcount=5,
    )


@pytest.fixture
def sample_balanced_trial_balance():
    return {
        "101": {"initial_credit": 5000.0, "final_credit": 5000.0},  # Registered Capital
        "121": {"initial_credit": 5680.0, "final_credit": 5680.0},  # Retained Earnings
        "204": {"initial_debit": 10000.0, "debit_turnover": 0.0, "final_debit": 10000.0},  # Equipment
        "241": {"initial_credit": 2000.0, "final_credit": 2000.0},  # Amortization -> Net Equipment 8000
        "304": {"initial_debit": 3000.0, "final_debit": 3000.0},  # Goods Inventory
        "411": {"initial_debit": 4000.0, "credit_turnover": 15000.0, "final_debit": 4000.0},  # Receivables
        "503": {"initial_debit": 5000.0, "final_debit": 10000.0},  # Bank account
        "401": {"initial_credit": 6000.0, "debit_turnover": 8000.0, "final_credit": 6000.0},  # Trade Payables
        "421": {"initial_credit": 2000.0, "debit_turnover": 4000.0, "final_credit": 2000.0},  # Personnel
        "455": {"initial_credit": 1000.0, "final_credit": 1000.0},  # Social Security
        "454": {"initial_credit": 520.0, "debit_turnover": 500.0, "final_credit": 1000.0},  # Taxes
        "601": {"debit_turnover": 2000.0},  # Materials
        "602": {"debit_turnover": 3000.0},  # Hired Services
        "604": {"debit_turnover": 4000.0},  # Salaries
        "605": {"debit_turnover": 1000.0},  # Social Sec Exp
        "621": {"debit_turnover": 200.0},   # Bank fees
        "702": {"credit_turnover": 20000.0, "debit_turnover": 5000.0},  # Revenue 20k, COGS 5k -> Net 15k
    }


class TestGFOGeneratorEngine:

    def test_generate_gfo_success(self, sample_company_profile, sample_balanced_trial_balance):
        report = GFOGeneratorEngine.generate_gfo(
            company_profile=sample_company_profile,
            trial_balance=sample_balanced_trial_balance,
            fiscal_year=2025,
        )

        assert isinstance(report, GFOReport)
        assert report.report_id == "GFO-123456789-2025"
        assert report.fiscal_year == 2025
        assert report.company_profile.company_name == "ТЕСТОВ БИЗНЕС ЕООД"
        assert len(report.document_hash_sha256) == 64

        # Income Statement checks
        assert report.income_statement.revenues.total_revenues == 20000.0
        assert report.income_statement.expenses.total_expenses == 15200.0
        assert report.income_statement.accounting_profit_loss_before_tax == 4800.0
        assert report.income_statement.corporate_tax_expense == 480.0
        assert report.income_statement.net_profit_loss == 4320.0

        # Balance Sheet Assets checks
        assert report.balance_sheet.assets.total_non_current_assets == 8000.0
        assert report.balance_sheet.assets.total_current_assets == 17000.0
        assert report.balance_sheet.assets.total_assets == 25000.0

        # Equity & Liabilities balance check
        assert report.balance_sheet.liabilities.total_equity_and_liabilities == 25000.0
        assert report.balance_sheet.is_balanced is True

    def test_validate_gfo_compliant(self, sample_company_profile, sample_balanced_trial_balance):
        report = GFOGeneratorEngine.generate_gfo(
            company_profile=sample_company_profile,
            trial_balance=sample_balanced_trial_balance,
            fiscal_year=2025,
        )

        validation = GFOGeneratorEngine.validate_gfo(report)
        assert isinstance(validation, GFOValidationResult)
        assert validation.is_valid is True
        assert validation.compliance_status == "COMPLIANT"
        assert len(validation.validation_errors) == 0

    def test_validate_gfo_imbalanced_detection(self, sample_company_profile):
        imbalanced_tb = {
            "101": {"final_credit": 1000.0},
            "503": {"final_debit": 5000.0},  # Assets 5000 != Liabilities 1000
        }
        report = GFOGeneratorEngine.generate_gfo(
            company_profile=sample_company_profile,
            trial_balance=imbalanced_tb,
            fiscal_year=2025,
        )
        validation = GFOGeneratorEngine.validate_gfo(report)
        assert validation.is_valid is False
        assert validation.compliance_status == "NON_COMPLIANT"
        assert any("Балансово различие" in err for err in validation.validation_errors)

    def test_export_commercial_register_xml(self, sample_company_profile, sample_balanced_trial_balance):
        report = GFOGeneratorEngine.generate_gfo(
            company_profile=sample_company_profile,
            trial_balance=sample_balanced_trial_balance,
            fiscal_year=2025,
        )
        xml_str = GFOGeneratorEngine.export_commercial_register_xml(report)
        assert "urn:bg:registryagency:gfo:v1" in xml_str
        ns = {"ns": "urn:bg:registryagency:gfo:v1"}
        root = ET.fromstring(xml_str)
        assert root.find(".//ns:EIK", ns).text == "123456789"
        assert root.find(".//ns:TotalAssets", ns).text == "25000.00"

    def test_export_printable_html(self, sample_company_profile, sample_balanced_trial_balance):
        report = GFOGeneratorEngine.generate_gfo(
            company_profile=sample_company_profile,
            trial_balance=sample_balanced_trial_balance,
            fiscal_year=2025,
        )
        html_str = GFOGeneratorEngine.export_printable_html(report)
        assert "ГОДИШЕН ФИНАНСОВ ОТЧЕТ" in html_str
        assert "ТЕСТОВ БИЗНЕС ЕООД" in html_str
        assert "123456789" in html_str
        assert "25,000.00" in html_str

    def test_generate_no_activity_declaration(self, sample_company_profile):
        decl = GFOGeneratorEngine.generate_no_activity_declaration(sample_company_profile, 2025)
        assert decl["declaration_type"] == "DECLARATION_ART_38_ALG_9_ZSCH"
        assert decl["eik"] == "123456789"
        assert "не е осъществявало дейност" in decl["statement"]
