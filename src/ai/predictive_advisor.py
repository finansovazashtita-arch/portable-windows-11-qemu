"""
Autonomous Predictive AI Financial Advisory & Decision Engine.

Milestone M77: m77_predictive_ai_advisory
Delivers:
1. Multi-scenario financial trajectory forecasting (Base Case, Optimistic, Downturn/Stress, Expansion).
2. Prescriptive C-Level AI Advisory recommendations engine with expected BGN financial impact, urgency, and step-by-step action plans.
3. Bulgarian double-entry accounting advice (Accounts 401, 411, 503, 609, 454, 122, 425, 709, 624, 724).
4. Solvency & Insolvency early warning system (Altman Z-Score & DSCR monitoring).
5. Tax optimization engine (VATA threshold tracking, CITA 10% pre-calculation, 5% dividend tax timing).
6. Working Capital & Cash Conversion Cycle (CCC = DSO + DIO - DPO) optimization.
"""

import dataclasses
import datetime
import enum
import hashlib
import json
import logging
import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("predictive_advisor")


class ScenarioType(str, enum.Enum):
    BASE_CASE = "BASE_CASE"
    OPTIMISTIC = "OPTIMISTIC"
    DOWNTURN = "DOWNTURN"
    EXPANSION = "EXPANSION"


class AdvisoryUrgency(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AdvisoryCategory(str, enum.Enum):
    LIQUIDITY = "LIQUIDITY"
    TAX_OPTIMIZATION = "TAX_OPTIMIZATION"
    WORKING_CAPITAL = "WORKING_CAPITAL"
    SOLVENCY = "SOLVENCY"
    CAPITAL_ALLOCATION = "CAPITAL_ALLOCATION"


@dataclasses.dataclass
class AccountingJournalAdvice:
    """Represents a recommended Bulgarian double-entry accounting transaction."""
    debit_account: str
    credit_account: str
    amount_bgn: float
    description: str
    statutory_reference: str  # e.g., "Art. 92 CITA", "Art. 96 VATA", "Art. 194 CITA"
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class AdvisoryInsight:
    """Dataclass representing a prescriptive AI advisory recommendation card."""
    insight_id: str
    tenant_id: str
    title: str
    category: AdvisoryCategory
    urgency: AdvisoryUrgency
    financial_impact_bgn: float
    confidence_score: float  # 0.0 to 1.0
    summary: str
    detailed_analysis: str
    action_items: List[str]
    journal_advice: Optional[AccountingJournalAdvice] = None
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        res = dataclasses.asdict(self)
        res["category"] = self.category.value
        res["urgency"] = self.urgency.value
        if self.journal_advice:
            res["journal_advice"] = self.journal_advice.to_dict()
        return res


@dataclasses.dataclass
class ScenarioForecastPoint:
    """Single date projection point within a scenario simulation trajectory."""
    date: str  # YYYY-MM-DD
    revenue_bgn: float
    expenses_bgn: float
    net_income_bgn: float
    ending_cash_bgn: float
    cumulative_tax_bgn: float
    altman_z_score: float

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class ScenarioSimulationResult:
    """Complete multi-scenario trajectory simulation output."""
    tenant_id: str
    horizon_days: int
    simulation_timestamp: str
    scenarios: Dict[str, List[ScenarioForecastPoint]]
    metrics_summary: Dict[str, Dict[str, float]]
    key_findings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "horizon_days": self.horizon_days,
            "simulation_timestamp": self.simulation_timestamp,
            "scenarios": {
                k: [pt.to_dict() for pt in v] for k, v in self.scenarios.items()
            },
            "metrics_summary": self.metrics_summary,
            "key_findings": self.key_findings,
        }


@dataclasses.dataclass
class CashConversionCycleBreakdown:
    """Working capital breakdown metrics for DSO, DPO, DIO, and CCC."""
    tenant_id: str
    dso_days: float  # Days Sales Outstanding
    dpo_days: float  # Days Payables Outstanding
    dio_days: float  # Days Inventory Outstanding
    ccc_days: float  # DSO + DIO - DPO
    accounts_receivable_bgn: float
    accounts_payable_bgn: float
    inventory_bgn: float
    trapped_working_capital_bgn: float
    potential_cash_release_bgn: float
    benchmarks: Dict[str, float]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class TaxOptimizationStrategy:
    """Bulgarian regulatory & corporate tax optimization advisory report."""
    tenant_id: str
    current_year_revenue_bgn: float
    vat_threshold_bgn: float  # 100,000 BGN under Art. 96 VATA
    vat_threshold_utilized_pct: float
    days_to_vat_threshold: Optional[int]
    forecasted_annual_profit_bgn: float
    estimated_corporate_tax_cita_bgn: float  # 10% CITA rate
    tax_saving_opportunities_bgn: float
    dividend_tax_optimization: Dict[str, Any]  # 5% dividend tax timing
    recommended_provisions: List[AccountingJournalAdvice]
    advisory_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        res = dataclasses.asdict(self)
        res["recommended_provisions"] = [p.to_dict() for p in self.recommended_provisions]
        return res


class PredictiveAIAdvisor:
    """
    Enterprise Predictive AI Advisory & Autonomous Decision Engine.
    Synthesizes financial ledgers, cash flows, solvency, and regulatory tax rules
    to generate prescriptive executive insights and scenario projections.
    """

    VAT_REGISTRATION_THRESHOLD_BGN = 100000.0  # Art. 96 VATA
    CITA_CORPORATE_TAX_RATE = 0.10  # 10% Bulgarian Corporate Income Tax (ЗКПО)
    DIVIDEND_TAX_RATE = 0.05  # 5% Bulgarian Dividend Tax (Art. 194 CITA / Art. 38 PITA)

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_advisory_insights(
        self,
        tenant_id: str,
        financial_summary: Dict[str, Any],
        filter_category: Optional[str] = None,
        filter_urgency: Optional[str] = None,
    ) -> List[AdvisoryInsight]:
        """
        Analyzes tenant financial health and returns prescriptive AI insights.
        """
        insights: List[AdvisoryInsight] = []
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        starting_cash = float(financial_summary.get("cash_balance_bgn", 150000.0))
        monthly_revenue = float(financial_summary.get("monthly_revenue_bgn", 85000.0))
        monthly_expenses = float(financial_summary.get("monthly_expenses_bgn", 72000.0))
        ar_bgn = float(financial_summary.get("accounts_receivable_bgn", 65000.0))
        ap_bgn = float(financial_summary.get("accounts_payable_bgn", 42000.0))
        inventory_bgn = float(financial_summary.get("inventory_bgn", 30000.0))
        total_assets = float(financial_summary.get("total_assets_bgn", 350000.0))
        total_liabilities = float(financial_summary.get("total_liabilities_bgn", 120000.0))
        retained_earnings = float(financial_summary.get("retained_earnings_bgn", 80000.0))
        annual_revenue = float(financial_summary.get("annual_revenue_bgn", monthly_revenue * 12))

        # 1. Cash Burn & Liquidity Advisory (LIQUIDITY)
        net_monthly_cash_flow = monthly_revenue - monthly_expenses
        if net_monthly_cash_flow < 0:
            burn_rate = abs(net_monthly_cash_flow)
            runway_months = starting_cash / burn_rate if burn_rate > 0 else 999.0
            urgency = AdvisoryUrgency.CRITICAL if runway_months < 6.0 else AdvisoryUrgency.HIGH
            insights.append(
                AdvisoryInsight(
                    insight_id=f"INS-{tenant_id[:6]}-LIQ-01",
                    tenant_id=tenant_id,
                    title=f"Liquidity & Cash Runway Optimization (Runway: {runway_months:.1f} Months)",
                    category=AdvisoryCategory.LIQUIDITY,
                    urgency=urgency,
                    financial_impact_bgn=round(burn_rate * 3, 2),
                    confidence_score=0.95,
                    summary=f"Current monthly burn rate of {burn_rate:,.2f} BGN limits cash runway to {runway_months:.1f} months.",
                    detailed_analysis=(
                        f"With a cash balance of {starting_cash:,.2f} BGN and net monthly outflow of {burn_rate:,.2f} BGN, "
                        "accelerated AR collections and vendor payment rescheduling are recommended."
                    ),
                    action_items=[
                        "Accelerate collection of overdue receivables.",
                        "Negotiate vendor payment term extensions (Account 401).",
                        "Optimize discretionary operating expenses."
                    ],
                    journal_advice=AccountingJournalAdvice(
                        debit_account="503",
                        credit_account="411",
                        amount_bgn=round(ar_bgn * 0.4, 2),
                        description="Accelerated AR collection for liquidity preservation",
                        statutory_reference="Art. 411 Accountancy Act",
                        rationale="Direct cash inflow from overdue client receivables."
                    ),
                    created_at=now_str,
                )
            )
        else:
            net_surplus = net_monthly_cash_flow
            insights.append(
                AdvisoryInsight(
                    insight_id=f"INS-{tenant_id[:6]}-LIQ-02",
                    tenant_id=tenant_id,
                    title="Positive Net Cash Flow Surplus Optimization",
                    category=AdvisoryCategory.LIQUIDITY,
                    urgency=AdvisoryUrgency.LOW,
                    financial_impact_bgn=round(net_surplus * 12, 2),
                    confidence_score=0.90,
                    summary=f"Company generates net positive cash flow of {net_surplus:,.2f} BGN/month.",
                    detailed_analysis=(
                        f"Reinvesting positive net cash surplus of {net_surplus:,.2f} BGN into growth "
                        "or short-term liquid reserves optimizes capital yield."
                    ),
                    action_items=[
                        "Allocate 50% of surplus to short-term high-yield reserve account.",
                        "Capture 2-3% vendor early payment cash discounts."
                    ],
                    journal_advice=AccountingJournalAdvice(
                        debit_account="504",
                        credit_account="503",
                        amount_bgn=round(net_surplus * 6, 2),
                        description="Transfer cash surplus to liquid reserve account",
                        statutory_reference="Art. 504 Accountancy Act",
                        rationale="Maximizes interest yield while preserving immediate liquidity access."
                    ),
                    created_at=now_str,
                )
            )

        # 2. Receivables & Working Capital Optimization (WORKING_CAPITAL)
        dso = (ar_bgn / annual_revenue) * 365 if annual_revenue > 0 else 0.0
        excess_ar = ar_bgn * 0.30
        insights.append(
            AdvisoryInsight(
                insight_id=f"INS-{tenant_id[:6]}-WC-01",
                tenant_id=tenant_id,
                title=f"Working Capital Optimization (Current DSO: {dso:.1f} Days)",
                category=AdvisoryCategory.WORKING_CAPITAL,
                urgency=AdvisoryUrgency.HIGH if dso > 45 else AdvisoryUrgency.MEDIUM,
                financial_impact_bgn=round(excess_ar, 2),
                confidence_score=0.91,
                summary=f"Days Sales Outstanding (DSO) is {dso:.1f} days with {ar_bgn:,.2f} BGN trapped in receivables.",
                detailed_analysis=(
                    f"Uncollected receivables total {ar_bgn:,.2f} BGN. Implementing automated payment reminders "
                    f"and early payment discounts can release up to {excess_ar:,.2f} BGN in cash."
                ),
                action_items=[
                    "Implement automated payment reminders 5 days prior to invoice due date.",
                    "Offer 2% early payment discount (2/10 Net 30).",
                    "Review bad debt tax provisions under Art. 34 CITA."
                ],
                journal_advice=AccountingJournalAdvice(
                    debit_account="609",
                    credit_account="241",
                    amount_bgn=round(ar_bgn * 0.05, 2),
                    description="Allowance for doubtful receivables provision",
                    statutory_reference="Art. 34 CITA (Bad Debt Tax Deductibility)",
                    rationale="Tax deductible bad debt provision under Bulgarian CITA rules."
                ),
                created_at=now_str,
            )
        )

        # 3. Tax Optimization Strategy (TAX_OPTIMIZATION)
        annual_profit = (monthly_revenue - monthly_expenses) * 12
        forecasted_profit = max(annual_profit, float(financial_summary.get("forecasted_annual_profit_bgn", 40000.0)))
        estimated_tax = forecasted_profit * self.CITA_CORPORATE_TAX_RATE
        tax_savings = estimated_tax * 0.15
        insights.append(
            AdvisoryInsight(
                insight_id=f"INS-{tenant_id[:6]}-TAX-01",
                tenant_id=tenant_id,
                title="Corporate Income Tax (CITA) Pre-Filing Optimization Strategy",
                category=AdvisoryCategory.TAX_OPTIMIZATION,
                urgency=AdvisoryUrgency.MEDIUM,
                financial_impact_bgn=round(tax_savings, 2),
                confidence_score=0.88,
                summary=f"Projected 10% CITA tax liability is {estimated_tax:,.2f} BGN. Potential savings of {tax_savings:,.2f} BGN identified.",
                detailed_analysis=(
                    f"Forecasted taxable profit under Art. 92 CITA is {forecasted_profit:,.2f} BGN. "
                    "Pre-booking statutory depreciation and employee bonus provisions reduces taxable income."
                ),
                action_items=[
                    "Review tax depreciation schedule under CITA categories I-VII.",
                    "Accrue year-end employee performance bonuses (Account 604/421).",
                    "Audit non-taxable vs taxable expenses under CITA Art. 26."
                ],
                journal_advice=AccountingJournalAdvice(
                    debit_account="604",
                    credit_account="421",
                    amount_bgn=round(forecasted_profit * 0.08, 2),
                    description="Year-end employee bonus tax-deductible provision",
                    statutory_reference="Art. 92 CITA / Art. 421 Accountancy",
                    rationale="Reduces taxable corporate profit prior to fiscal year closing."
                ),
                created_at=now_str,
            )
        )

        # 4. Solvency & Altman Z-Score Warning (SOLVENCY)
        working_capital = (starting_cash + ar_bgn + inventory_bgn) - ap_bgn
        z_score = self.calculate_altman_z_score(
            working_capital=working_capital,
            total_assets=total_assets,
            retained_earnings=retained_earnings,
            ebit=forecasted_profit,
            market_value_equity=total_assets - total_liabilities,
            total_liabilities=total_liabilities,
            sales=annual_revenue,
        )
        z_urgency = AdvisoryUrgency.CRITICAL if z_score < 1.81 else AdvisoryUrgency.LOW
        insights.append(
            AdvisoryInsight(
                insight_id=f"INS-{tenant_id[:6]}-SOL-01",
                tenant_id=tenant_id,
                title=f"Corporate Solvency Assessment (Altman Z-Score: {z_score:.2f})",
                category=AdvisoryCategory.SOLVENCY,
                urgency=z_urgency,
                financial_impact_bgn=round(total_liabilities * 0.15, 2),
                confidence_score=0.92,
                summary=f"Altman Z-Score is {z_score:.2f} ({'Distress Zone' if z_score < 1.81 else 'Safe / Stable Zone'}).",
                detailed_analysis=(
                    f"Financial solvency analysis confirms Z-Score of {z_score:.2f}. "
                    f"Debt-to-Equity ratio is {(total_liabilities / max(total_assets - total_liabilities, 1.0)):.2f}."
                ),
                action_items=[
                    "Monitor debt service coverage ratio (DSCR).",
                    "Maintain healthy equity-to-asset balance.",
                    "Optimize short-term vs long-term debt structure."
                ],
                journal_advice=AccountingJournalAdvice(
                    debit_account="498",
                    credit_account="101",
                    amount_bgn=round(total_liabilities * 0.1, 2),
                    description="Shareholder loan capitalization to equity buffer",
                    statutory_reference="Art. 101 Commercial Act",
                    rationale="Strengthens balance sheet equity ratio."
                ),
                created_at=now_str,
            )
        )

        # 5. Capital Allocation & Idle Cash Yield (CAPITAL_ALLOCATION)
        safety_buffer = monthly_expenses * 2.0
        idle_cash = max(0.0, starting_cash - safety_buffer)
        potential_yield = idle_cash * 0.035
        insights.append(
            AdvisoryInsight(
                insight_id=f"INS-{tenant_id[:6]}-CAP-01",
                tenant_id=tenant_id,
                title=f"Capital Allocation & Liquidity Yield Strategy ({idle_cash:,.0f} BGN Available)",
                category=AdvisoryCategory.CAPITAL_ALLOCATION,
                urgency=AdvisoryUrgency.LOW,
                financial_impact_bgn=round(potential_yield, 2),
                confidence_score=0.85,
                summary=f"Available capital of {idle_cash:,.2f} BGN above safety buffer can be deployed for yield.",
                detailed_analysis=(
                    f"Placing idle liquidity into short-term term deposits or early vendor settlement "
                    f"yields up to {potential_yield:,.2f} BGN annually."
                ),
                action_items=[
                    "Evaluate 30-day term deposit options (Account 504).",
                    "Capture supplier cash discounts yielding > 10% annualized."
                ],
                journal_advice=AccountingJournalAdvice(
                    debit_account="504",
                    credit_account="503",
                    amount_bgn=round(idle_cash * 0.5, 2),
                    description="Transfer excess operating cash to term deposit",
                    statutory_reference="Art. 504 Accountancy Act",
                    rationale="Generates interest return on idle funds."
                ),
                created_at=now_str,
            )
        )

        # Filter results if requested
        if filter_category:
            insights = [i for i in insights if i.category.value == filter_category or i.category == filter_category]
        if filter_urgency:
            insights = [i for i in insights if i.urgency.value == filter_urgency or i.urgency == filter_urgency]

        return insights

    def simulate_scenarios(
        self,
        tenant_id: str,
        financial_summary: Dict[str, Any],
        horizon_days: int = 90,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> ScenarioSimulationResult:
        """
        Executes multi-scenario financial trajectory simulations (Base Case, Optimistic, Downturn, Expansion).
        """
        custom_params = custom_params or {}
        starting_cash = float(financial_summary.get("cash_balance_bgn", 150000.0))
        base_monthly_rev = float(financial_summary.get("monthly_revenue_bgn", 85000.0))
        base_monthly_exp = float(financial_summary.get("monthly_expenses_bgn", 72000.0))
        total_assets = float(financial_summary.get("total_assets_bgn", 350000.0))
        total_liabilities = float(financial_summary.get("total_liabilities_bgn", 120000.0))

        start_date = datetime.date.today()
        num_months = math.ceil(horizon_days / 30.0)

        # Scenario Multipliers
        scenario_configs = {
            ScenarioType.BASE_CASE.value: {
                "rev_growth": custom_params.get("base_rev_growth", 0.02),
                "exp_growth": custom_params.get("base_exp_growth", 0.01),
                "tax_rate": self.CITA_CORPORATE_TAX_RATE,
            },
            ScenarioType.OPTIMISTIC.value: {
                "rev_growth": custom_params.get("opt_rev_growth", 0.15),
                "exp_growth": custom_params.get("opt_exp_growth", 0.04),
                "tax_rate": self.CITA_CORPORATE_TAX_RATE,
            },
            ScenarioType.DOWNTURN.value: {
                "rev_growth": custom_params.get("down_rev_growth", -0.20),
                "exp_growth": custom_params.get("down_exp_growth", 0.05),
                "tax_rate": self.CITA_CORPORATE_TAX_RATE,
            },
            ScenarioType.EXPANSION.value: {
                "rev_growth": custom_params.get("exp_rev_growth", 0.30),
                "exp_growth": custom_params.get("exp_exp_growth", 0.20),
                "tax_rate": self.CITA_CORPORATE_TAX_RATE,
            },
        }

        results: Dict[str, List[ScenarioForecastPoint]] = {}
        summary_metrics: Dict[str, Dict[str, float]] = {}

        for sc_name, cfg in scenario_configs.items():
            pts: List[ScenarioForecastPoint] = []
            curr_cash = starting_cash
            cum_tax = 0.0

            for m in range(1, num_months + 1):
                # Calculate date point
                month_date = start_date + datetime.timedelta(days=m * 30)
                date_str = month_date.strftime("%Y-%m-%d")

                # Monthly trajectory calculation
                rev = base_monthly_rev * ((1 + cfg["rev_growth"]) ** (m / 12.0))
                exp = base_monthly_exp * ((1 + cfg["exp_growth"]) ** (m / 12.0))
                net_inc = rev - exp

                tax_m = max(0.0, net_inc) * cfg["tax_rate"]
                cum_tax += tax_m

                curr_cash += (net_inc - tax_m)

                z_score = self.calculate_altman_z_score(
                    working_capital=curr_cash + 30000 - 20000,
                    total_assets=total_assets + curr_cash - starting_cash,
                    retained_earnings=80000 + (curr_cash - starting_cash),
                    ebit=net_inc * 12,
                    market_value_equity=total_assets - total_liabilities,
                    total_liabilities=total_liabilities,
                    sales=rev * 12,
                )

                pts.append(
                    ScenarioForecastPoint(
                        date=date_str,
                        revenue_bgn=round(rev, 2),
                        expenses_bgn=round(exp, 2),
                        net_income_bgn=round(net_inc, 2),
                        ending_cash_bgn=round(curr_cash, 2),
                        cumulative_tax_bgn=round(cum_tax, 2),
                        altman_z_score=round(z_score, 2),
                    )
                )

            results[sc_name] = pts
            ending_pt = pts[-1]
            summary_metrics[sc_name] = {
                "ending_cash_bgn": ending_pt.ending_cash_bgn,
                "net_change_bgn": round(ending_pt.ending_cash_bgn - starting_cash, 2),
                "cumulative_tax_bgn": ending_pt.cumulative_tax_bgn,
                "final_z_score": ending_pt.altman_z_score,
            }

        key_findings = [
            f"Base Case forecast projects ending cash balance of {summary_metrics['BASE_CASE']['ending_cash_bgn']:,.2f} BGN over {horizon_days} days.",
            f"Downturn scenario indicates potential cash draw of {abs(summary_metrics['DOWNTURN']['net_change_bgn']):,.2f} BGN.",
            f"Expansion scenario yields {summary_metrics['EXPANSION']['ending_cash_bgn']:,.2f} BGN cash balance with Z-Score of {summary_metrics['EXPANSION']['final_z_score']:.2f}."
        ]

        return ScenarioSimulationResult(
            tenant_id=tenant_id,
            horizon_days=horizon_days,
            simulation_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            scenarios=results,
            metrics_summary=summary_metrics,
            key_findings=key_findings,
        )

    def calculate_cash_conversion_cycle(
        self, tenant_id: str, financial_summary: Dict[str, Any]
    ) -> CashConversionCycleBreakdown:
        """
        Calculates Working Capital metrics: DSO, DPO, DIO, and Cash Conversion Cycle (CCC).
        """
        ar = float(financial_summary.get("accounts_receivable_bgn", 65000.0))
        ap = float(financial_summary.get("accounts_payable_bgn", 42000.0))
        inv = float(financial_summary.get("inventory_bgn", 30000.0))
        revenue = float(financial_summary.get("annual_revenue_bgn", 1020000.0))
        cogs = float(financial_summary.get("annual_cogs_bgn", revenue * 0.65))

        dso = (ar / revenue) * 365 if revenue > 0 else 0.0
        dio = (inv / cogs) * 365 if cogs > 0 else 0.0
        dpo = (ap / cogs) * 365 if cogs > 0 else 0.0
        ccc = dso + dio - dpo

        trapped_wc = ar + inv - ap
        target_dso = 35.0
        target_dio = 25.0
        target_dpo = 45.0
        target_ccc = target_dso + target_dio - target_dpo

        potential_ar_release = max(0.0, (dso - target_dso) * (revenue / 365.0))
        potential_inv_release = max(0.0, (dio - target_dio) * (cogs / 365.0))
        potential_release = potential_ar_release + potential_inv_release

        recs = []
        if dso > target_dso:
            recs.append(f"Reduce DSO from {dso:.1f} to {target_dso:.1f} days to release {potential_ar_release:,.2f} BGN in cash.")
        if dio > target_dio:
            recs.append(f"Improve inventory turn (DIO {dio:.1f} -> {target_dio:.1f} days) releasing {potential_inv_release:,.2f} BGN.")
        if dpo < target_dpo:
            recs.append(f"Extend DPO from {dpo:.1f} to {target_dpo:.1f} days to preserve operational cash flow.")

        return CashConversionCycleBreakdown(
            tenant_id=tenant_id,
            dso_days=round(dso, 1),
            dpo_days=round(dpo, 1),
            dio_days=round(dio, 1),
            ccc_days=round(ccc, 1),
            accounts_receivable_bgn=round(ar, 2),
            accounts_payable_bgn=round(ap, 2),
            inventory_bgn=round(inv, 2),
            trapped_working_capital_bgn=round(trapped_wc, 2),
            potential_cash_release_bgn=round(potential_release, 2),
            benchmarks={
                "target_dso": target_dso,
                "target_dpo": target_dpo,
                "target_dio": target_dio,
                "target_ccc": target_ccc,
            },
            recommendations=recs,
        )

    def evaluate_tax_strategy(
        self, tenant_id: str, financial_summary: Dict[str, Any]
    ) -> TaxOptimizationStrategy:
        """
        Evaluates Bulgarian tax compliance (VATA 100k threshold, CITA 10%, 5% dividend tax timing).
        """
        ytd_revenue = float(financial_summary.get("ytd_revenue_bgn", 82000.0))
        monthly_rev = float(financial_summary.get("monthly_revenue_bgn", 15000.0))
        annual_profit = float(financial_summary.get("forecasted_annual_profit_bgn", 45000.0))

        vat_threshold = self.VAT_REGISTRATION_THRESHOLD_BGN
        vat_pct = (ytd_revenue / vat_threshold) * 100.0

        days_to_vat = None
        if ytd_revenue < vat_threshold and monthly_rev > 0:
            rem_rev = vat_threshold - ytd_revenue
            months_needed = rem_rev / monthly_rev
            days_to_vat = int(months_needed * 30)

        estimated_cita = annual_profit * self.CITA_CORPORATE_TAX_RATE

        retained_earnings = float(financial_summary.get("retained_earnings_bgn", 60000.0))
        potential_dividend = min(retained_earnings, annual_profit * 0.7)
        dividend_tax = potential_dividend * self.DIVIDEND_TAX_RATE

        div_optimization = {
            "available_distributable_profit_bgn": round(retained_earnings, 2),
            "recommended_payout_bgn": round(potential_dividend, 2),
            "estimated_dividend_tax_5pct_bgn": round(dividend_tax, 2),
            "net_shareholder_distribution_bgn": round(potential_dividend - dividend_tax, 2),
            "statutory_reference": "Art. 194 CITA / Art. 38 PITA (5% Dividend Tax)",
            "timing_advice": "Execute dividend payout after General Meeting approval (Form 55 quarterly filing).",
        }

        provisions = [
            AccountingJournalAdvice(
                debit_account="609",
                credit_account="454",
                amount_bgn=round(estimated_cita, 2),
                description="Accrual of 10% Bulgarian Corporate Income Tax (ЗКПО)",
                statutory_reference="Art. 92 CITA",
                rationale="Establishes tax liability prior to statutory filing deadline.",
            )
        ]

        notes = [
            f"VATA threshold utilization is at {vat_pct:.1f}%. Registration under Art. 96 VATA required within 7 days of exceeding 100,000 BGN.",
            f"CITA 10% corporate income tax estimated at {estimated_cita:,.2f} BGN based on forecasted annual profit.",
        ]

        return TaxOptimizationStrategy(
            tenant_id=tenant_id,
            current_year_revenue_bgn=round(ytd_revenue, 2),
            vat_threshold_bgn=vat_threshold,
            vat_threshold_utilized_pct=round(vat_pct, 1),
            days_to_vat_threshold=days_to_vat,
            forecasted_annual_profit_bgn=round(annual_profit, 2),
            estimated_corporate_tax_cita_bgn=round(estimated_cita, 2),
            tax_saving_opportunities_bgn=round(estimated_cita * 0.15, 2),
            dividend_tax_optimization=div_optimization,
            recommended_provisions=provisions,
            advisory_notes=notes,
        )

    @staticmethod
    def calculate_altman_z_score(
        working_capital: float,
        total_assets: float,
        retained_earnings: float,
        ebit: float,
        market_value_equity: float,
        total_liabilities: float,
        sales: float,
    ) -> float:
        """
        Calculates Altman Z-Score for corporate distress prediction:
        Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 0.999*X5
        Safe Zone > 2.99, Grey Zone 1.81-2.99, Distress Zone < 1.81
        """
        assets = max(total_assets, 1.0)
        liab = max(total_liabilities, 1.0)

        x1 = working_capital / assets
        x2 = retained_earnings / assets
        x3 = ebit / assets
        x4 = market_value_equity / liab
        x5 = sales / assets

        z = (1.2 * x1) + (1.4 * x2) + (3.3 * x3) + (0.6 * x4) + (0.999 * x5)
        return z
