"""
Financial & Operational KPI Calculator Module (Milestone M76).

Computes core financial metrics, profitability ratios, liquidity indicators,
AR/AP aging buckets, SaaS subscription KPIs, and growth rates for C-level dashboards.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class FinancialKPIs:
    gross_revenue: float = 0.0
    net_revenue: float = 0.0
    operating_expenses: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    ebitda: float = 0.0
    net_profit: float = 0.0
    net_margin_pct: float = 0.0
    cash_balance: float = 0.0
    operating_cash_flow: float = 0.0
    monthly_burn_rate: float = 0.0
    cash_runway_months: float = 0.0


@dataclass
class ARAPAging:
    total_ar: float = 0.0
    total_ap: float = 0.0
    dso_days: float = 0.0
    dpo_days: float = 0.0
    ar_aging_0_30: float = 0.0
    ar_aging_31_60: float = 0.0
    ar_aging_61_90: float = 0.0
    ar_aging_90_plus: float = 0.0
    ap_aging_0_30: float = 0.0
    ap_aging_31_60: float = 0.0
    ap_aging_61_90: float = 0.0
    ap_aging_90_plus: float = 0.0


@dataclass
class SaasKPIs:
    mrr: float = 0.0
    arr: float = 0.0
    arpu: float = 0.0
    active_subscribers: int = 0
    churn_rate_pct: float = 0.0
    cac: float = 0.0
    ltv: float = 0.0
    ltv_cac_ratio: float = 0.0


@dataclass
class GrowthMetrics:
    mom_revenue_growth_pct: float = 0.0
    yoy_revenue_growth_pct: float = 0.0
    mom_expense_growth_pct: float = 0.0
    net_margin_change_bps: float = 0.0


@dataclass
class KPISummary:
    financials: FinancialKPIs = field(default_factory=FinancialKPIs)
    ar_ap: ARAPAging = field(default_factory=ARAPAging)
    saas: SaasKPIs = field(default_factory=SaasKPIs)
    growth: GrowthMetrics = field(default_factory=GrowthMetrics)
    currency: str = "BGN"
    period: str = "monthly"
    tenant_id: Optional[str] = None
    calculated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "financials": {
                "gross_revenue": round(self.financials.gross_revenue, 2),
                "net_revenue": round(self.financials.net_revenue, 2),
                "operating_expenses": round(self.financials.operating_expenses, 2),
                "gross_profit": round(self.financials.gross_profit, 2),
                "gross_margin_pct": round(self.financials.gross_margin_pct, 2),
                "ebitda": round(self.financials.ebitda, 2),
                "net_profit": round(self.financials.net_profit, 2),
                "net_margin_pct": round(self.financials.net_margin_pct, 2),
                "cash_balance": round(self.financials.cash_balance, 2),
                "operating_cash_flow": round(self.financials.operating_cash_flow, 2),
                "monthly_burn_rate": round(self.financials.monthly_burn_rate, 2),
                "cash_runway_months": round(self.financials.cash_runway_months, 1),
            },
            "ar_ap": {
                "total_ar": round(self.ar_ap.total_ar, 2),
                "total_ap": round(self.ar_ap.total_ap, 2),
                "dso_days": round(self.ar_ap.dso_days, 1),
                "dpo_days": round(self.ar_ap.dpo_days, 1),
                "ar_aging_buckets": {
                    "0_30_days": round(self.ar_ap.ar_aging_0_30, 2),
                    "31_60_days": round(self.ar_ap.ar_aging_31_60, 2),
                    "61_90_days": round(self.ar_ap.ar_aging_61_90, 2),
                    "90_plus_days": round(self.ar_ap.ar_aging_90_plus, 2),
                },
                "ap_aging_buckets": {
                    "0_30_days": round(self.ar_ap.ap_aging_0_30, 2),
                    "31_60_days": round(self.ar_ap.ap_aging_31_60, 2),
                    "61_90_days": round(self.ar_ap.ap_aging_61_90, 2),
                    "90_plus_days": round(self.ar_ap.ap_aging_90_plus, 2),
                },
            },
            "saas": {
                "mrr": round(self.saas.mrr, 2),
                "arr": round(self.saas.arr, 2),
                "arpu": round(self.saas.arpu, 2),
                "active_subscribers": self.saas.active_subscribers,
                "churn_rate_pct": round(self.saas.churn_rate_pct, 2),
                "cac": round(self.saas.cac, 2),
                "ltv": round(self.saas.ltv, 2),
                "ltv_cac_ratio": round(self.saas.ltv_cac_ratio, 2),
            },
            "growth": {
                "mom_revenue_growth_pct": round(self.growth.mom_revenue_growth_pct, 2),
                "yoy_revenue_growth_pct": round(self.growth.yoy_revenue_growth_pct, 2),
                "mom_expense_growth_pct": round(self.growth.mom_expense_growth_pct, 2),
                "net_margin_change_bps": round(self.growth.net_margin_change_bps, 2),
            },
            "metadata": {
                "currency": self.currency,
                "period": self.period,
                "tenant_id": self.tenant_id,
                "calculated_at": self.calculated_at,
            },
        }


class KPICalculator:
    """Core financial and business intelligence KPI calculation engine."""

    @staticmethod
    def calculate_financials(
        gross_revenue: float,
        cost_of_goods_sold: float,
        operating_expenses: float,
        tax_expenses: float,
        depreciation_amortization: float,
        cash_balance: float,
        cash_inflows: float,
        cash_outflows: float,
    ) -> FinancialKPIs:
        """Compute primary income statement and cash balance KPIs."""
        gross_revenue = float(gross_revenue or 0.0)
        cogs = float(cost_of_goods_sold or 0.0)
        opex = float(operating_expenses or 0.0)
        tax = float(tax_expenses or 0.0)
        da = float(depreciation_amortization or 0.0)

        net_revenue = max(0.0, gross_revenue)
        gross_profit = net_revenue - cogs
        gross_margin_pct = (gross_profit / net_revenue * 100.0) if net_revenue > 0 else 0.0

        net_profit = gross_profit - opex - tax - da
        net_margin_pct = (net_profit / net_revenue * 100.0) if net_revenue > 0 else 0.0

        ebitda = net_profit + tax + da

        cash_balance = float(cash_balance or 0.0)
        operating_cash_flow = float(cash_inflows or 0.0) - float(cash_outflows or 0.0)

        # Monthly burn rate calculation: net negative cash flow
        monthly_burn = max(0.0, float(cash_outflows or 0.0) - float(cash_inflows or 0.0))
        if monthly_burn == 0.0 and opex > 0:
            monthly_burn = opex

        cash_runway = (cash_balance / monthly_burn) if (monthly_burn > 0 and cash_balance > 0) else 999.0

        return FinancialKPIs(
            gross_revenue=gross_revenue,
            net_revenue=net_revenue,
            operating_expenses=opex,
            gross_profit=gross_profit,
            gross_margin_pct=gross_margin_pct,
            ebitda=ebitda,
            net_profit=net_profit,
            net_margin_pct=net_margin_pct,
            cash_balance=cash_balance,
            operating_cash_flow=operating_cash_flow,
            monthly_burn_rate=monthly_burn,
            cash_runway_months=cash_runway,
        )

    @staticmethod
    def calculate_ar_ap(
        ar_items: List[Dict[str, Any]],
        ap_items: List[Dict[str, Any]],
        period_days: int = 365,
        total_credit_sales: float = 0.0,
        total_credit_purchases: float = 0.0,
    ) -> ARAPAging:
        """Compute AR/AP aging buckets and DSO/DPO efficiency ratios."""
        tot_ar = 0.0
        ar_0_30 = 0.0
        ar_31_60 = 0.0
        ar_61_90 = 0.0
        ar_90_plus = 0.0

        for item in ar_items:
            amt = float(item.get("amount", 0.0))
            age = int(item.get("age_days", 0))
            tot_ar += amt
            if age <= 30:
                ar_0_30 += amt
            elif age <= 60:
                ar_31_60 += amt
            elif age <= 90:
                ar_61_90 += amt
            else:
                ar_90_plus += amt

        tot_ap = 0.0
        ap_0_30 = 0.0
        ap_31_60 = 0.0
        ap_61_90 = 0.0
        ap_90_plus = 0.0

        for item in ap_items:
            amt = float(item.get("amount", 0.0))
            age = int(item.get("age_days", 0))
            tot_ap += amt
            if age <= 30:
                ap_0_30 += amt
            elif age <= 60:
                ap_31_60 += amt
            elif age <= 90:
                ap_61_90 += amt
            else:
                ap_90_plus += amt

        # DSO = (Total AR / Credit Sales) * period_days
        dso = (tot_ar / total_credit_sales * period_days) if total_credit_sales > 0 else 0.0
        # DPO = (Total AP / Cost of Goods / Purchases) * period_days
        dpo = (tot_ap / total_credit_purchases * period_days) if total_credit_purchases > 0 else 0.0

        return ARAPAging(
            total_ar=tot_ar,
            total_ap=tot_ap,
            dso_days=dso,
            dpo_days=dpo,
            ar_aging_0_30=ar_0_30,
            ar_aging_31_60=ar_31_60,
            ar_aging_61_90=ar_61_90,
            ar_aging_90_plus=ar_90_plus,
            ap_aging_0_30=ap_0_30,
            ap_aging_31_60=ap_31_60,
            ap_aging_61_90=ap_61_90,
            ap_aging_90_plus=ap_90_plus,
        )

    @staticmethod
    def calculate_saas(
        subscriptions: List[Dict[str, Any]],
        churned_count: int = 0,
        marketing_sales_spend: float = 0.0,
        new_subscribers_count: int = 0,
        gross_margin_pct: float = 80.0,
    ) -> SaasKPIs:
        """Compute SaaS recurring revenue, ARPU, churn, CAC, and LTV metrics."""
        mrr = 0.0
        active_subs = 0

        for sub in subscriptions:
            status = str(sub.get("status", "active")).lower()
            if status == "active":
                price = float(sub.get("price", 0.0))
                interval = str(sub.get("interval", "month")).lower()
                if interval == "year":
                    mrr += price / 12.0
                else:
                    mrr += price
                active_subs += 1

        arr = mrr * 12.0
        arpu = (mrr / active_subs) if active_subs > 0 else 0.0

        total_users = active_subs + churned_count
        churn_rate = (churned_count / total_users * 100.0) if total_users > 0 else 0.0

        cac = (marketing_sales_spend / new_subscribers_count) if new_subscribers_count > 0 else 0.0

        # LTV = ARPU * Gross Margin % / Churn Rate decimal
        churn_decimal = (churn_rate / 100.0) if churn_rate > 0 else 0.05
        ltv = (arpu * (gross_margin_pct / 100.0) / churn_decimal) if churn_decimal > 0 else (arpu * 24)

        ltv_cac_ratio = (ltv / cac) if cac > 0 else 0.0

        return SaasKPIs(
            mrr=mrr,
            arr=arr,
            arpu=arpu,
            active_subscribers=active_subs,
            churn_rate_pct=churn_rate,
            cac=cac,
            ltv=ltv,
            ltv_cac_ratio=ltv_cac_ratio,
        )

    @staticmethod
    def calculate_growth(
        current_revenue: float,
        prior_month_revenue: float,
        prior_year_revenue: float,
        current_expense: float,
        prior_month_expense: float,
        current_net_margin_pct: float,
        prior_net_margin_pct: float,
    ) -> GrowthMetrics:
        """Calculate MoM/YoY growth percentages and margin variance in basis points."""
        mom_rev = (
            ((current_revenue - prior_month_revenue) / prior_month_revenue * 100.0)
            if prior_month_revenue > 0
            else 0.0
        )
        yoy_rev = (
            ((current_revenue - prior_year_revenue) / prior_year_revenue * 100.0)
            if prior_year_revenue > 0
            else 0.0
        )
        mom_exp = (
            ((current_expense - prior_month_expense) / prior_month_expense * 100.0)
            if prior_month_expense > 0
            else 0.0
        )

        margin_bps = (current_net_margin_pct - prior_net_margin_pct) * 100.0

        return GrowthMetrics(
            mom_revenue_growth_pct=mom_rev,
            yoy_revenue_growth_pct=yoy_rev,
            mom_expense_growth_pct=mom_exp,
            net_margin_change_bps=margin_bps,
        )
