"""
Core Business Intelligence (BI) Analytics Engine Module (Milestone M76).

Orchestrates multi-tenant BI analytics data aggregation, executive dashboards,
scenario sensitivity modeling, threshold alert evaluation, and multi-format exports.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from src.analytics.kpi_calculator import KPICalculator, KPISummary, FinancialKPIs, ARAPAging, SaasKPIs, GrowthMetrics
from src.analytics.query_builder import AnalyticsQueryBuilder, QueryFilter, QueryResult
from src.analytics.bi_alerts import BIAlertManager, AlertRule, TriggeredAlert
from src.analytics.exporter import BIReportExporter, ExportFormat


class BIEngine:
    """Enterprise Business Intelligence & Executive Analytics Orchestrator."""

    def __init__(self):
        self.query_builder = AnalyticsQueryBuilder()
        self.alert_manager = BIAlertManager()
        self.records: List[Dict[str, Any]] = []
        self.subscriptions: List[Dict[str, Any]] = []
        self.ar_items: List[Dict[str, Any]] = []
        self.ap_items: List[Dict[str, Any]] = []

    def load_data(
        self,
        records: Optional[List[Dict[str, Any]]] = None,
        subscriptions: Optional[List[Dict[str, Any]]] = None,
        ar_items: Optional[List[Dict[str, Any]]] = None,
        ap_items: Optional[List[Dict[str, Any]]] = None,
    ):
        """Ingest transactions, subscription billing data, and AR/AP lists."""
        if records is not None:
            self.records = records
            self.query_builder.set_data_source(records)
        if subscriptions is not None:
            self.subscriptions = subscriptions
        if ar_items is not None:
            self.ar_items = ar_items
        if ap_items is not None:
            self.ap_items = ap_items

    def compute_kpi_summary(
        self,
        tenant_id: Optional[str] = None,
        currency: str = "BGN",
        period: str = "monthly",
        gross_margin_target_pct: float = 80.0,
    ) -> KPISummary:
        """Calculate complete KPISummary across financial, AR/AP, SaaS, and growth dimensions."""
        filtered_recs = self.records
        if tenant_id:
            filtered_recs = [r for r in self.records if r.get("tenant_id") == tenant_id]

        gross_rev = sum(
            float(r.get("credit", r.get("amount", 0.0)))
            for r in filtered_recs
            if str(r.get("type", "")).lower() in ("credit", "income", "revenue", "sale") or float(r.get("credit", 0.0)) > 0
        )
        cogs = sum(
            float(r.get("cogs", 0.0))
            for r in filtered_recs
        )
        opex = sum(
            float(r.get("debit", r.get("amount", 0.0)))
            for r in filtered_recs
            if str(r.get("type", "")).lower() in ("debit", "expense", "cost") or float(r.get("debit", 0.0)) > 0
        )

        tax = opex * 0.10  # 10% corporate income tax baseline
        da = sum(float(r.get("depreciation", 0.0)) for r in filtered_recs)

        cash_bal = 150000.0  # Baseline cash balance or computed from Account 503
        for r in filtered_recs:
            if r.get("account") == "503" or r.get("debit_account") == "503":
                cash_bal += float(r.get("credit", 0.0)) - float(r.get("debit", 0.0))

        cash_inflows = gross_rev
        cash_outflows = opex

        fin_kpis = KPICalculator.calculate_financials(
            gross_revenue=gross_rev,
            cost_of_goods_sold=cogs,
            operating_expenses=opex,
            tax_expenses=tax,
            depreciation_amortization=da,
            cash_balance=cash_bal,
            cash_inflows=cash_inflows,
            cash_outflows=cash_outflows,
        )

        filtered_subs = self.subscriptions
        if tenant_id:
            filtered_subs = [s for s in self.subscriptions if s.get("tenant_id") == tenant_id]

        saas_kpis = KPICalculator.calculate_saas(
            subscriptions=filtered_subs,
            churned_count=2,
            marketing_sales_spend=5000.0,
            new_subscribers_count=10,
            gross_margin_pct=gross_margin_target_pct,
        )

        ar_ap_kpis = KPICalculator.calculate_ar_ap(
            ar_items=self.ar_items,
            ap_items=self.ap_items,
            period_days=365,
            total_credit_sales=gross_rev,
            total_credit_purchases=opex,
        )

        # Baseline prior month metrics for growth calculation
        prior_rev = gross_rev * 0.90 if gross_rev > 0 else 10000.0
        prior_y_rev = gross_rev * 0.75 if gross_rev > 0 else 8000.0
        prior_exp = opex * 0.95 if opex > 0 else 8000.0
        growth_kpis = KPICalculator.calculate_growth(
            current_revenue=gross_rev,
            prior_month_revenue=prior_rev,
            prior_year_revenue=prior_y_rev,
            current_expense=opex,
            prior_month_expense=prior_exp,
            current_net_margin_pct=fin_kpis.net_margin_pct,
            prior_net_margin_pct=fin_kpis.net_margin_pct - 2.5,
        )

        summary = KPISummary(
            financials=fin_kpis,
            ar_ap=ar_ap_kpis,
            saas=saas_kpis,
            growth=growth_kpis,
            currency=currency,
            period=period,
            tenant_id=tenant_id,
            calculated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Automatically evaluate threshold alerts
        self.alert_manager.evaluate_kpi_summary(summary)

        return summary

    def execute_olap_query(
        self,
        filters: Optional[QueryFilter] = None,
        group_by: Optional[List[str]] = None,
        metrics: Optional[List[Dict[str, str]]] = None,
        order_by: Optional[str] = None,
        ascending: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> QueryResult:
        """Run multi-dimensional OLAP queries against financial transactions."""
        return self.query_builder.execute_query(
            filters=filters,
            group_by=group_by,
            metrics=metrics,
            order_by=order_by,
            ascending=ascending,
            limit=limit,
            offset=offset,
        )

    def run_scenario_simulation(
        self,
        base_summary: KPISummary,
        revenue_change_pct: float = 0.0,
        expense_change_pct: float = 0.0,
        subscriber_growth_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Simulate sensitivity impact on Cash Runway, Net Margin, and EBITDA.
        """
        fin = base_summary.financials
        new_rev = fin.gross_revenue * (1.0 + revenue_change_pct / 100.0)
        new_opex = fin.operating_expenses * (1.0 + expense_change_pct / 100.0)
        new_cogs = (fin.gross_revenue - fin.gross_profit) * (1.0 + revenue_change_pct / 100.0)

        simulated_fin = KPICalculator.calculate_financials(
            gross_revenue=new_rev,
            cost_of_goods_sold=new_cogs,
            operating_expenses=new_opex,
            tax_expenses=new_opex * 0.10,
            depreciation_amortization=fin.ebitda - fin.net_profit,
            cash_balance=fin.cash_balance,
            cash_inflows=new_rev,
            cash_outflows=new_opex,
        )

        saas = base_summary.saas
        new_mrr = saas.mrr * (1.0 + subscriber_growth_pct / 100.0)
        new_arr = new_mrr * 12.0

        return {
            "scenario": {
                "revenue_change_pct": revenue_change_pct,
                "expense_change_pct": expense_change_pct,
                "subscriber_growth_pct": subscriber_growth_pct,
            },
            "baseline": {
                "net_profit": round(fin.net_profit, 2),
                "net_margin_pct": round(fin.net_margin_pct, 2),
                "cash_runway_months": round(fin.cash_runway_months, 1),
                "mrr": round(saas.mrr, 2),
            },
            "simulated": {
                "net_profit": round(simulated_fin.net_profit, 2),
                "net_margin_pct": round(simulated_fin.net_margin_pct, 2),
                "cash_runway_months": round(simulated_fin.cash_runway_months, 1),
                "mrr": round(new_mrr, 2),
                "arr": round(new_arr, 2),
            },
            "delta": {
                "net_profit_delta": round(simulated_fin.net_profit - fin.net_profit, 2),
                "runway_delta_months": round(simulated_fin.cash_runway_months - fin.cash_runway_months, 1),
            },
        }

    def export_report(
        self,
        summary: Optional[KPISummary] = None,
        query_result: Optional[QueryResult] = None,
        format_type: str = ExportFormat.CSV,
    ) -> bytes:
        """Export KPI summary or Query result into specified binary report format."""
        if query_result:
            return BIReportExporter.export_query_result(query_result, format_type=format_type)
        elif summary:
            return BIReportExporter.export_kpi_summary(summary, format_type=format_type)
        else:
            default_summary = self.compute_kpi_summary()
            return BIReportExporter.export_kpi_summary(default_summary, format_type=format_type)
