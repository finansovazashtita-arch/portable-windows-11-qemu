"""
Autonomous Enterprise GFO Generator Engine (M72).

Generates, reconciles, validates, and exports Bulgarian Annual Financial Statements
(ГФО - Годишен Финансов Отчет) under the Bulgarian Accounting Act (Закон за счетоводството - ЗСч),
National Accounting Standards (НСФО), CITA (ЗКПО), and Commercial Register / NRA / NSI standards.
"""

import dataclasses
import datetime
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger("gfo_generator")


@dataclasses.dataclass
class CompanyEntityProfile:
    """Legal entity metadata for statutory filing."""

    company_name: str
    eik: str  # EIK / Bulstat (9 or 13 digits)
    address: str
    manager_name: str
    vat_number: Optional[str] = None
    accounting_standard: str = "NAS"  # "NAS" (НСФО) or "IFRS" (ИФРС)
    economic_activity_code: Optional[str] = None  # КИД-2008
    headcount: int = 1


@dataclasses.dataclass
class TrialBalanceAccount:
    """Trial Balance account balances and turnovers (Оборотна ведомост)."""

    account_code: str
    account_name: str
    initial_debit: float = 0.0
    initial_credit: float = 0.0
    debit_turnover: float = 0.0
    credit_turnover: float = 0.0
    final_debit: float = 0.0
    final_credit: float = 0.0


@dataclasses.dataclass
class BalanceSheetAssets:
    """Statutory Balance Sheet - Assets breakdown (Счетоводен баланс - Активи)."""

    intangible_assets: float = 0.0  # Сметки 201
    tangible_fixed_assets: float = 0.0  # Сметки 203, 204, 205 по нето амортизация 241
    long_term_financial_assets: float = 0.0  # Сметка 221
    total_non_current_assets: float = 0.0  # Сума ДМА/ДНА

    inventories: float = 0.0  # Сметки 301, 302, 304
    short_term_receivables: float = 0.0  # Сметки 411, 422, 498
    cash_and_cash_equivalents: float = 0.0  # Сметки 501, 503
    deferred_expenses: float = 0.0
    total_current_assets: float = 0.0  # Сума Краткотрайни активи

    total_assets: float = 0.0


@dataclasses.dataclass
class BalanceSheetLiabilities:
    """Statutory Balance Sheet - Equity & Liabilities breakdown (Счетоводен баланс - Пасиви)."""

    registered_capital: float = 0.0  # Сметка 101
    share_premium_reserves: float = 0.0  # Сметка 111
    statutory_legal_reserves: float = 0.0  # Сметка 117
    retained_earnings_past_years: float = 0.0  # Сметки 121 / 122
    current_year_net_result: float = 0.0  # Сметка 123
    total_equity: float = 0.0  # Сума Собствен капитал

    long_term_loans: float = 0.0  # Сметки 151, 152
    other_non_current_liabilities: float = 0.0
    total_non_current_liabilities: float = 0.0

    trade_payables: float = 0.0  # Сметка 401
    payables_to_personnel: float = 0.0  # Сметка 421
    social_security_payables: float = 0.0  # Сметка 455
    tax_payables: float = 0.0  # Сметка 454
    other_current_liabilities: float = 0.0
    total_current_liabilities: float = 0.0

    total_equity_and_liabilities: float = 0.0


@dataclasses.dataclass
class BalanceSheet:
    """Statutory Balance Sheet (Счетоводен баланс)."""

    assets: BalanceSheetAssets
    liabilities: BalanceSheetLiabilities
    is_balanced: bool
    imbalance_amount: float


@dataclasses.dataclass
class IncomeStatementExpenses:
    """Statutory Income Statement - Expenses breakdown (ОПР - Разходи)."""

    raw_materials_and_supplies: float = 0.0  # Сметка 601
    hired_services: float = 0.0  # Сметка 602
    depreciation_and_amortization: float = 0.0  # Сметка 603
    personnel_salaries: float = 0.0  # Сметка 604
    social_security_contributions: float = 0.0  # Сметка 605
    other_operating_expenses: float = 0.0  # Сметка 609
    cogs_cost_of_goods_sold: float = 0.0  # Сметка 702 (себестойност)
    financial_expenses: float = 0.0  # Сметки 621, 624
    extraordinary_expenses: float = 0.0

    total_operating_expenses: float = 0.0
    total_financial_expenses: float = 0.0
    total_expenses: float = 0.0


@dataclasses.dataclass
class IncomeStatementRevenues:
    """Statutory Income Statement - Revenues breakdown (ОПР - Приходи)."""

    sales_of_production_and_goods: float = 0.0  # Сметки 701, 702
    sales_of_services: float = 0.0  # Сметка 703
    other_operating_revenues: float = 0.0  # Сметка 709
    financial_revenues: float = 0.0  # Сметка 724
    extraordinary_revenues: float = 0.0

    total_operating_revenues: float = 0.0
    total_financial_revenues: float = 0.0
    total_revenues: float = 0.0


@dataclasses.dataclass
class IncomeStatement:
    """Statutory Income Statement (Отчет за приходите и разходите - ОПР)."""

    expenses: IncomeStatementExpenses
    revenues: IncomeStatementRevenues
    accounting_profit_loss_before_tax: float
    corporate_tax_expense: float
    net_profit_loss: float


@dataclasses.dataclass
class CashFlowStatement:
    """Statutory Statement of Cash Flows (Отчет за паричните потоци - ОПП)."""

    operating_cash_inflow: float = 0.0
    operating_cash_outflow: float = 0.0
    net_operating_cash_flow: float = 0.0

    investing_cash_inflow: float = 0.0
    investing_cash_outflow: float = 0.0
    net_investing_cash_flow: float = 0.0

    financing_cash_inflow: float = 0.0
    financing_cash_outflow: float = 0.0
    net_financing_cash_flow: float = 0.0

    net_change_in_cash: float = 0.0
    beginning_cash_balance: float = 0.0
    ending_cash_balance: float = 0.0


@dataclasses.dataclass
class ChangesInEquityStatement:
    """Statutory Statement of Changes in Equity (Отчет за собствения капитал - ОСК)."""

    beginning_equity: float = 0.0
    capital_contributions: float = 0.0
    dividends_distributed: float = 0.0
    current_net_profit_loss: float = 0.0
    ending_equity: float = 0.0


@dataclasses.dataclass
class ExplanatoryNotes:
    """Explanatory Notes and Disclosures (Приложение)."""

    company_name: str
    eik: str
    fiscal_year: int
    accounting_policy_summary: str
    valuation_bases: str
    subsequent_events: str


@dataclasses.dataclass
class GFOReport:
    """Complete statutory Annual Financial Statement (Годишен Финансов Отчет)."""

    report_id: str
    company_profile: CompanyEntityProfile
    fiscal_year: int
    generated_at: str
    balance_sheet: BalanceSheet
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement
    changes_in_equity: ChangesInEquityStatement
    explanatory_notes: ExplanatoryNotes
    document_hash_sha256: str


@dataclasses.dataclass
class GFOValidationResult:
    """Audit & Compliance Validation Result."""

    is_valid: bool
    compliance_status: str  # "COMPLIANT", "NON_COMPLIANT", "ZERO_ACTIVITY"
    validation_errors: List[str]
    warning_messages: List[str]
    audited_at: str


class GFOGeneratorEngine:
    """Autonomous Engine orchestrating GFO generation, statutory validation, and export."""

    @classmethod
    def generate_gfo(
        cls,
        company_profile: CompanyEntityProfile,
        trial_balance: Dict[str, Dict[str, float]],
        fiscal_year: int,
    ) -> GFOReport:
        """
        Generates full GFO Report from Trial Balance dictionary mapping.
        
        trial_balance format:
        {
            "account_code": {
                "initial_debit": float, "initial_credit": float,
                "debit_turnover": float, "credit_turnover": float,
                "final_debit": float, "final_credit": float
            }
        }
        """
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        report_id = f"GFO-{company_profile.eik}-{fiscal_year}"

        # Step 1: Parse Income Statement (ОПР)
        expenses = cls._build_income_statement_expenses(trial_balance)
        revenues = cls._build_income_statement_revenues(trial_balance)

        profit_before_tax = round(revenues.total_revenues - expenses.total_expenses, 2)
        corporate_tax = round(max(0.0, profit_before_tax * 0.10), 2) if profit_before_tax > 0 else 0.0
        net_profit_loss = round(profit_before_tax - corporate_tax, 2)

        income_stmt = IncomeStatement(
            expenses=expenses,
            revenues=revenues,
            accounting_profit_loss_before_tax=profit_before_tax,
            corporate_tax_expense=corporate_tax,
            net_profit_loss=net_profit_loss,
        )

        # Step 2: Parse Balance Sheet (Баланс)
        assets = cls._build_balance_sheet_assets(trial_balance)
        liabilities = cls._build_balance_sheet_liabilities(trial_balance, net_profit_loss)

        total_assets = round(assets.total_assets, 2)
        total_liab_equity = round(liabilities.total_equity_and_liabilities, 2)
        imbalance = round(abs(total_assets - total_liab_equity), 2)
        is_balanced = imbalance < 0.01

        balance_sheet = BalanceSheet(
            assets=assets,
            liabilities=liabilities,
            is_balanced=is_balanced,
            imbalance_amount=imbalance,
        )

        # Step 3: Parse Cash Flow Statement (ОПП)
        cash_flow = cls._build_cash_flow_statement(trial_balance)

        # Step 4: Parse Changes in Equity (ОСК)
        equity_changes = cls._build_changes_in_equity(trial_balance, net_profit_loss)

        # Step 5: Explanatory Notes (Приложение)
        notes = ExplanatoryNotes(
            company_name=company_profile.company_name,
            eik=company_profile.eik,
            fiscal_year=fiscal_year,
            accounting_policy_summary=(
                f"Финансовият отчет е съставен в съответствие с {company_profile.accounting_standard}."
            ),
            valuation_bases="ДМА и ДНА са оценени по цена на придобиване намалена с натрупаната амортизация.",
            subsequent_events="Няма настъпили съществени събития след датата на баланса.",
        )

        # Compute document SHA-256 hash
        payload_data = {
            "report_id": report_id,
            "eik": company_profile.eik,
            "fiscal_year": fiscal_year,
            "total_assets": total_assets,
            "net_profit_loss": net_profit_loss,
        }
        hash_digest = hashlib.sha256(json.dumps(payload_data, sort_keys=True).encode("utf-8")).hexdigest()

        gfo_report = GFOReport(
            report_id=report_id,
            company_profile=company_profile,
            fiscal_year=fiscal_year,
            generated_at=now_str,
            balance_sheet=balance_sheet,
            income_statement=income_stmt,
            cash_flow_statement=cash_flow,
            changes_in_equity=equity_changes,
            explanatory_notes=notes,
            document_hash_sha256=hash_digest,
        )

        logger.info(
            f"📊 GFO Generator [{company_profile.company_name} ({fiscal_year})]: "
            f"Assets=€{total_assets:,.2f}, Equity&Liab=€{total_liab_equity:,.2f}, Net Result=€{net_profit_loss:,.2f}."
        )
        return gfo_report

    @classmethod
    def validate_gfo(cls, report: GFOReport) -> GFOValidationResult:
        """Audits and validates statutory compliance of the generated GFO."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Balance sheet equality check
        if not report.balance_sheet.is_balanced:
            errors.append(
                f"Балансово различие (Assets €{report.balance_sheet.assets.total_assets:,.2f} ≠ "
                f"Equity & Liabilities €{report.balance_sheet.liabilities.total_equity_and_liabilities:,.2f}, "
                f"Разлика: €{report.balance_sheet.imbalance_amount:,.2f})"
            )

        # 2. Check current profit consistency between Income Statement and Balance Sheet Equity
        if abs(report.income_statement.net_profit_loss - report.balance_sheet.liabilities.current_year_net_result) > 0.01:
            errors.append(
                f"Несъответствие в текущия резултат: ОПР (€{report.income_statement.net_profit_loss:,.2f}) ≠ "
                f"Баланс Пасив с/ка 123 (€{report.balance_sheet.liabilities.current_year_net_result:,.2f})"
            )

        # 3. Check cash flow ending balance matches cash asset balance
        if abs(report.cash_flow_statement.ending_cash_balance - report.balance_sheet.assets.cash_and_cash_equivalents) > 0.01:
            warnings.append(
                f"Разлика в паричните средства: ОПП крайна наличност (€{report.cash_flow_statement.ending_cash_balance:,.2f}) ≠ "
                f"Баланс Активи с/ки 501+503 (€{report.balance_sheet.assets.cash_and_cash_equivalents:,.2f})"
            )

        # 4. Check mandatory entity metadata
        if not report.company_profile.eik or len(report.company_profile.eik) not in (9, 13):
            errors.append(f"Невалиден ЕИК / БУЛСТАТ код: {report.company_profile.eik}")
        if not report.company_profile.manager_name:
            errors.append("Липсва име на представляващия управител")

        # Check zero-activity status
        is_zero_activity = (
            report.income_statement.revenues.total_revenues == 0.0
            and report.income_statement.expenses.total_expenses == 0.0
            and report.balance_sheet.assets.total_assets == report.balance_sheet.liabilities.registered_capital
        )

        compliance_status = "ZERO_ACTIVITY" if is_zero_activity else ("COMPLIANT" if not errors else "NON_COMPLIANT")
        is_valid = len(errors) == 0

        return GFOValidationResult(
            is_valid=is_valid,
            compliance_status=compliance_status,
            validation_errors=errors,
            warning_messages=warnings,
            audited_at=now_str,
        )

    @classmethod
    def export_commercial_register_xml(cls, report: GFOReport) -> str:
        """Exports statutory XML payload compliant with Commercial Register (Търговски регистър)."""
        root = ET.Element("GFOReport", xmlns="urn:bg:registryagency:gfo:v1")
        
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "ReportID").text = report.report_id
        ET.SubElement(header, "FiscalYear").text = str(report.fiscal_year)
        ET.SubElement(header, "GeneratedAt").text = report.generated_at
        ET.SubElement(header, "DocumentHash").text = report.document_hash_sha256

        company = ET.SubElement(root, "Company")
        ET.SubElement(company, "Name").text = report.company_profile.company_name
        ET.SubElement(company, "EIK").text = report.company_profile.eik
        ET.SubElement(company, "Address").text = report.company_profile.address
        ET.SubElement(company, "Manager").text = report.company_profile.manager_name

        bs = ET.SubElement(root, "BalanceSheet")
        assets_el = ET.SubElement(bs, "Assets")
        ET.SubElement(assets_el, "NonCurrentAssets").text = f"{report.balance_sheet.assets.total_non_current_assets:.2f}"
        ET.SubElement(assets_el, "CurrentAssets").text = f"{report.balance_sheet.assets.total_current_assets:.2f}"
        ET.SubElement(assets_el, "TotalAssets").text = f"{report.balance_sheet.assets.total_assets:.2f}"

        liab_el = ET.SubElement(bs, "LiabilitiesAndEquity")
        ET.SubElement(liab_el, "TotalEquity").text = f"{report.balance_sheet.liabilities.total_equity:.2f}"
        ET.SubElement(liab_el, "CurrentLiabilities").text = f"{report.balance_sheet.liabilities.total_current_liabilities:.2f}"
        ET.SubElement(liab_el, "TotalLiabilitiesAndEquity").text = f"{report.balance_sheet.liabilities.total_equity_and_liabilities:.2f}"

        is_el = ET.SubElement(root, "IncomeStatement")
        ET.SubElement(is_el, "TotalRevenues").text = f"{report.income_statement.revenues.total_revenues:.2f}"
        ET.SubElement(is_el, "TotalExpenses").text = f"{report.income_statement.expenses.total_expenses:.2f}"
        ET.SubElement(is_el, "NetProfitLoss").text = f"{report.income_statement.net_profit_loss:.2f}"

        return ET.tostring(root, encoding="utf-8").decode("utf-8")

    @classmethod
    def export_canonical_json(cls, report: GFOReport) -> Dict[str, Any]:
        """Exports canonical JSON structure."""
        return dataclasses.asdict(report)

    @classmethod
    def export_printable_html(cls, report: GFOReport) -> str:
        """Generates statutory printable HTML document for signing and physical audit files."""
        html = f"""<!DOCTYPE html>
<html lang="bg">
<head>
    <meta charset="UTF-8">
    <title>ГОДИШЕН ФИНАНСОВ ОТЧЕТ - {report.company_profile.company_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #111; }}
        h1, h2, h3 {{ text-align: center; color: #1e293b; }}
        .meta-table, .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; }}
        .data-table th, .data-table td {{ border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }}
        .data-table th {{ background-color: #f1f5f9; }}
        .num {{ text-align: right; font-family: monospace; }}
        .total-row {{ font-weight: bold; background-color: #e2e8f0; }}
        .signature-box {{ margin-top: 50px; display: flex; justify-content: space-between; }}
    </style>
</head>
<body>
    <h1>ГОДИШЕН ФИНАНСОВ ОТЧЕТ</h1>
    <h2>за {report.fiscal_year} година</h2>
    <h3>на "{report.company_profile.company_name}" (ЕИК: {report.company_profile.eik})</h3>

    <table class="meta-table">
        <tr><td><strong>Адрес на управление:</strong> {report.company_profile.address}</td></tr>
        <tr><td><strong>Представляващ:</strong> {report.company_profile.manager_name}</td></tr>
        <tr><td><strong>Приложим стандарт:</strong> {report.company_profile.accounting_standard}</td></tr>
    </table>

    <h2>1. СЧЕТОВОДЕН БАЛАНС</h2>
    <table class="data-table">
        <thead>
            <tr><th>АКТИВИ</th><th class="num">Сума (BGN / EUR)</th></tr>
        </thead>
        <tbody>
            <tr><td>Дълготрайни материални и нематериални активи</td><td class="num">{report.balance_sheet.assets.total_non_current_assets:,.2f}</td></tr>
            <tr><td>Материални запаси</td><td class="num">{report.balance_sheet.assets.inventories:,.2f}</td></tr>
            <tr><td>Вземания от клиенти и други</td><td class="num">{report.balance_sheet.assets.short_term_receivables:,.2f}</td></tr>
            <tr><td>Парични средства (Каса и Банкови сметки)</td><td class="num">{report.balance_sheet.assets.cash_and_cash_equivalents:,.2f}</td></tr>
            <tr class="total-row"><td>ОБЩО АКТИВИ</td><td class="num">{report.balance_sheet.assets.total_assets:,.2f}</td></tr>
        </tbody>
    </table>

    <table class="data-table">
        <thead>
            <tr><th>ПАСИВИ И СОБСТВЕН КАПИТАЛ</th><th class="num">Сума (BGN / EUR)</th></tr>
        </thead>
        <tbody>
            <tr><td>Основен и резервен капитал</td><td class="num">{report.balance_sheet.liabilities.registered_capital + report.balance_sheet.liabilities.statutory_legal_reserves:,.2f}</td></tr>
            <tr><td>Натрупана и текуща печалба / загуба</td><td class="num">{report.balance_sheet.liabilities.retained_earnings_past_years + report.balance_sheet.liabilities.current_year_net_result:,.2f}</td></tr>
            <tr><td>Задължения към доставчици, персонал и данъци</td><td class="num">{report.balance_sheet.liabilities.total_current_liabilities:,.2f}</td></tr>
            <tr class="total-row"><td>ОБЩО ПАСИВИ И СОБСТВЕН КАПИТАЛ</td><td class="num">{report.balance_sheet.liabilities.total_equity_and_liabilities:,.2f}</td></tr>
        </tbody>
    </table>

    <h2>2. ОТЧЕТ ЗА ПРИХОДИТЕ И РАЗХОДИТЕ (ОПР)</h2>
    <table class="data-table">
        <thead>
            <tr><th>Показател</th><th class="num">Приходи</th><th class="num">Разходи</th></tr>
        </thead>
        <tbody>
            <tr><td>Оперативна дейност (Продажби / Материали / Услуги / Заплати)</td><td class="num">{report.income_statement.revenues.total_operating_revenues:,.2f}</td><td class="num">{report.income_statement.expenses.total_operating_expenses:,.2f}</td></tr>
            <tr><td>Финансова дейност (Курсови разлики / Банкови такси)</td><td class="num">{report.income_statement.revenues.total_financial_revenues:,.2f}</td><td class="num">{report.income_statement.expenses.total_financial_expenses:,.2f}</td></tr>
            <tr class="total-row"><td>ОБЩО СУМИ</td><td class="num">{report.income_statement.revenues.total_revenues:,.2f}</td><td class="num">{report.income_statement.expenses.total_expenses:,.2f}</td></tr>
            <tr class="total-row"><td>НЕТЕН ФИНАНСОВ РЕЗУЛТАТ (ПЕЧАЛБА / ЗАГУБА)</td><td colspan="2" class="num">{report.income_statement.net_profit_loss:,.2f}</td></tr>
        </tbody>
    </table>

    <div class="signature-box">
        <div>
            <p>Управител: ..............................</p>
            <p>({report.company_profile.manager_name})</p>
        </div>
        <div>
            <p>Съставител: ..............................</p>
            <p>(Главен Счетоводител)</p>
        </div>
    </div>
</body>
</html>"""
        return html

    @classmethod
    def generate_no_activity_declaration(cls, company_profile: CompanyEntityProfile, fiscal_year: int) -> Dict[str, Any]:
        """Generates Art. 38(9) Accounting Act Declaration of No Activity for non-operating companies."""
        return {
            "declaration_type": "DECLARATION_ART_38_ALG_9_ZSCH",
            "company_name": company_profile.company_name,
            "eik": company_profile.eik,
            "fiscal_year": fiscal_year,
            "manager_name": company_profile.manager_name,
            "statement": (
                f"Долуподписаният {company_profile.manager_name}, в качеството си на управител на "
                f'"{company_profile.company_name}" (ЕИК {company_profile.eik}), декларирам, че за '
                f"финансовата {fiscal_year} година предприятието не е осъществявало дейност по смисъла на ЗСч."
            ),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    # Private Mapping Helpers
    @classmethod
    def _get_acc_val(cls, tb: Dict[str, Dict[str, float]], code: str, field: str = "final_debit") -> float:
        acc = tb.get(code, {})
        return round(acc.get(field, 0.0), 2)

    @classmethod
    def _build_balance_sheet_assets(cls, tb: Dict[str, Dict[str, float]]) -> BalanceSheetAssets:
        intangible = cls._get_acc_val(tb, "201")
        fixed_tangible = cls._get_acc_val(tb, "203") + cls._get_acc_val(tb, "204") + cls._get_acc_val(tb, "205")
        depreciation = cls._get_acc_val(tb, "241", "final_credit")
        net_tangible = max(0.0, fixed_tangible - depreciation)
        fin_assets = cls._get_acc_val(tb, "221")

        total_non_current = round(intangible + net_tangible + fin_assets, 2)

        inventories = cls._get_acc_val(tb, "301") + cls._get_acc_val(tb, "302") + cls._get_acc_val(tb, "304")
        receivables = cls._get_acc_val(tb, "411") + cls._get_acc_val(tb, "422") + cls._get_acc_val(tb, "498")
        cash = cls._get_acc_val(tb, "501") + cls._get_acc_val(tb, "503")

        total_current = round(inventories + receivables + cash, 2)
        total_assets = round(total_non_current + total_current, 2)

        return BalanceSheetAssets(
            intangible_assets=intangible,
            tangible_fixed_assets=net_tangible,
            long_term_financial_assets=fin_assets,
            total_non_current_assets=total_non_current,
            inventories=inventories,
            short_term_receivables=receivables,
            cash_and_cash_equivalents=cash,
            total_current_assets=total_current,
            total_assets=total_assets,
        )

    @classmethod
    def _build_balance_sheet_liabilities(
        cls, tb: Dict[str, Dict[str, float]], net_profit_loss: float
    ) -> BalanceSheetLiabilities:
        registered_cap = cls._get_acc_val(tb, "101", "final_credit")
        share_premium = cls._get_acc_val(tb, "111", "final_credit")
        stat_reserves = cls._get_acc_val(tb, "117", "final_credit")

        retained_profit = cls._get_acc_val(tb, "121", "final_credit")
        retained_loss = cls._get_acc_val(tb, "122", "final_debit")
        retained_net = retained_profit - retained_loss

        # Account 123 balance or passed net_profit_loss
        curr_result = cls._get_acc_val(tb, "123", "final_credit") - cls._get_acc_val(tb, "123", "final_debit")
        if curr_result == 0.0:
            curr_result = net_profit_loss

        total_equity = round(registered_cap + share_premium + stat_reserves + retained_net + curr_result, 2)

        long_loans = cls._get_acc_val(tb, "151", "final_credit") + cls._get_acc_val(tb, "152", "final_credit")
        total_non_current_liab = round(long_loans, 2)

        trade_payables = cls._get_acc_val(tb, "401", "final_credit")
        personnel_payables = cls._get_acc_val(tb, "421", "final_credit")
        social_sec = cls._get_acc_val(tb, "455", "final_credit")
        tax_payables = cls._get_acc_val(tb, "454", "final_credit")
        other_current = cls._get_acc_val(tb, "499", "final_credit")

        total_current_liab = round(trade_payables + personnel_payables + social_sec + tax_payables + other_current, 2)

        total_eq_liab = round(total_equity + total_non_current_liab + total_current_liab, 2)

        return BalanceSheetLiabilities(
            registered_capital=registered_cap,
            share_premium_reserves=share_premium,
            statutory_legal_reserves=stat_reserves,
            retained_earnings_past_years=retained_net,
            current_year_net_result=curr_result,
            total_equity=total_equity,
            long_term_loans=long_loans,
            total_non_current_liabilities=total_non_current_liab,
            trade_payables=trade_payables,
            payables_to_personnel=personnel_payables,
            social_security_payables=social_sec,
            tax_payables=tax_payables,
            other_current_liabilities=other_current,
            total_current_liabilities=total_current_liab,
            total_equity_and_liabilities=total_eq_liab,
        )

    @classmethod
    def _build_income_statement_expenses(cls, tb: Dict[str, Dict[str, float]]) -> IncomeStatementExpenses:
        mat = cls._get_acc_val(tb, "601", "debit_turnover")
        serv = cls._get_acc_val(tb, "602", "debit_turnover")
        depr = cls._get_acc_val(tb, "603", "debit_turnover")
        sal = cls._get_acc_val(tb, "604", "debit_turnover")
        soc = cls._get_acc_val(tb, "605", "debit_turnover")
        other_op = cls._get_acc_val(tb, "609", "debit_turnover")
        cogs = cls._get_acc_val(tb, "702", "debit_turnover")

        tot_op = round(mat + serv + depr + sal + soc + other_op + cogs, 2)

        fin_exp = cls._get_acc_val(tb, "621", "debit_turnover") + cls._get_acc_val(tb, "624", "debit_turnover")
        tot_fin = round(fin_exp, 2)
        tot_exp = round(tot_op + tot_fin, 2)

        return IncomeStatementExpenses(
            raw_materials_and_supplies=mat,
            hired_services=serv,
            depreciation_and_amortization=depr,
            personnel_salaries=sal,
            social_security_contributions=soc,
            other_operating_expenses=other_op,
            cogs_cost_of_goods_sold=cogs,
            financial_expenses=fin_exp,
            total_operating_expenses=tot_op,
            total_financial_expenses=tot_fin,
            total_expenses=tot_exp,
        )

    @classmethod
    def _build_income_statement_revenues(cls, tb: Dict[str, Dict[str, float]]) -> IncomeStatementRevenues:
        prod_goods = cls._get_acc_val(tb, "701", "credit_turnover") + cls._get_acc_val(tb, "702", "credit_turnover")
        services = cls._get_acc_val(tb, "703", "credit_turnover")
        other_op = cls._get_acc_val(tb, "709", "credit_turnover")

        tot_op = round(prod_goods + services + other_op, 2)

        fin_rev = cls._get_acc_val(tb, "724", "credit_turnover")
        tot_fin = round(fin_rev, 2)
        tot_rev = round(tot_op + tot_fin, 2)

        return IncomeStatementRevenues(
            sales_of_production_and_goods=prod_goods,
            sales_of_services=services,
            other_operating_revenues=other_op,
            financial_revenues=fin_rev,
            total_operating_revenues=tot_op,
            total_financial_revenues=tot_fin,
            total_revenues=tot_rev,
        )

    @classmethod
    def _build_cash_flow_statement(cls, tb: Dict[str, Dict[str, float]]) -> CashFlowStatement:
        op_in = cls._get_acc_val(tb, "411", "credit_turnover")
        op_out = (
            cls._get_acc_val(tb, "401", "debit_turnover")
            + cls._get_acc_val(tb, "421", "debit_turnover")
            + cls._get_acc_val(tb, "454", "debit_turnover")
        )
        net_op = round(op_in - op_out, 2)

        inv_in = 0.0
        inv_out = cls._get_acc_val(tb, "204", "debit_turnover")
        net_inv = round(inv_in - inv_out, 2)

        fin_in = cls._get_acc_val(tb, "151", "credit_turnover")
        fin_out = cls._get_acc_val(tb, "425", "debit_turnover")
        net_fin = round(fin_in - fin_out, 2)

        net_change = round(net_op + net_inv + net_fin, 2)

        beg_cash = cls._get_acc_val(tb, "501", "initial_debit") + cls._get_acc_val(tb, "503", "initial_debit")
        end_cash = cls._get_acc_val(tb, "501", "final_debit") + cls._get_acc_val(tb, "503", "final_debit")

        return CashFlowStatement(
            operating_cash_inflow=op_in,
            operating_cash_outflow=op_out,
            net_operating_cash_flow=net_op,
            investing_cash_inflow=inv_in,
            investing_cash_outflow=inv_out,
            net_investing_cash_flow=net_inv,
            financing_cash_inflow=fin_in,
            financing_cash_outflow=fin_out,
            net_financing_cash_flow=net_fin,
            net_change_in_cash=net_change,
            beginning_cash_balance=beg_cash,
            ending_cash_balance=end_cash,
        )

    @classmethod
    def _build_changes_in_equity(
        cls, tb: Dict[str, Dict[str, float]], net_profit_loss: float
    ) -> ChangesInEquityStatement:
        beg_cap = (
            cls._get_acc_val(tb, "101", "initial_credit")
            + cls._get_acc_val(tb, "111", "initial_credit")
            + cls._get_acc_val(tb, "117", "initial_credit")
            + cls._get_acc_val(tb, "121", "initial_credit")
            - cls._get_acc_val(tb, "122", "initial_debit")
        )
        div = cls._get_acc_val(tb, "425", "debit_turnover")
        end_cap = round(beg_cap - div + net_profit_loss, 2)

        return ChangesInEquityStatement(
            beginning_equity=beg_cap,
            capital_contributions=0.0,
            dividends_distributed=div,
            current_net_profit_loss=net_profit_loss,
            ending_equity=end_cap,
        )
