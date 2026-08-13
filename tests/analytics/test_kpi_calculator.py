"""
Unit Tests for Financial & Operational KPI Calculator (Milestone M76).
"""

import pytest
from src.analytics.kpi_calculator import KPICalculator, FinancialKPIs, ARAPAging, SaasKPIs, GrowthMetrics, KPISummary


class TestKPICalculator:

    def test_calculate_financials_normal(self):
        fin = KPICalculator.calculate_financials(
            gross_revenue=100000.0,
            cost_of_goods_sold=20000.0,
            operating_expenses=30000.0,
            tax_expenses=5000.0,
            depreciation_amortization=2000.0,
            cash_balance=150000.0,
            cash_inflows=100000.0,
            cash_outflows=37000.0,
        )
        assert fin.gross_revenue == 100000.0
        assert fin.gross_profit == 80000.0
        assert fin.gross_margin_pct == 80.0
        assert fin.net_profit == 43000.0  # 80000 - 30000 - 5000 - 2000
        assert fin.net_margin_pct == 43.0
        assert fin.ebitda == 50000.0  # 43000 + 5000 + 2000
        assert fin.operating_cash_flow == 63000.0

    def test_calculate_financials_zero_revenue(self):
        fin = KPICalculator.calculate_financials(
            gross_revenue=0.0,
            cost_of_goods_sold=0.0,
            operating_expenses=10000.0,
            tax_expenses=0.0,
            depreciation_amortization=0.0,
            cash_balance=50000.0,
            cash_inflows=0.0,
            cash_outflows=10000.0,
        )
        assert fin.gross_margin_pct == 0.0
        assert fin.net_margin_pct == 0.0
        assert fin.net_profit == -10000.0
        assert fin.monthly_burn_rate == 10000.0
        assert fin.cash_runway_months == 5.0

    def test_calculate_ar_ap_aging(self):
        ar = [
            {"amount": 10000.0, "age_days": 15},
            {"amount": 5000.0, "age_days": 45},
            {"amount": 3000.0, "age_days": 75},
            {"amount": 2000.0, "age_days": 100},
        ]
        ap = [
            {"amount": 8000.0, "age_days": 20},
            {"amount": 4000.0, "age_days": 95},
        ]
        aging = KPICalculator.calculate_ar_ap(
            ar_items=ar,
            ap_items=ap,
            period_days=365,
            total_credit_sales=200000.0,
            total_credit_purchases=120000.0,
        )
        assert aging.total_ar == 20000.0
        assert aging.ar_aging_0_30 == 10000.0
        assert aging.ar_aging_31_60 == 5000.0
        assert aging.ar_aging_61_90 == 3000.0
        assert aging.ar_aging_90_plus == 2000.0
        assert aging.total_ap == 12000.0
        assert aging.ap_aging_0_30 == 8000.0
        assert aging.ap_aging_90_plus == 4000.0
        assert round(aging.dso_days, 1) == 36.5  # (20000/200000)*365
        assert round(aging.dpo_days, 1) == 36.5  # (12000/120000)*365

    def test_calculate_saas_metrics(self):
        subs = [
            {"tenant_id": "t1", "status": "active", "price": 500.0, "interval": "month"},
            {"tenant_id": "t2", "status": "active", "price": 1200.0, "interval": "year"},  # 100/mo
            {"tenant_id": "t3", "status": "cancelled", "price": 300.0, "interval": "month"},
        ]
        saas = KPICalculator.calculate_saas(
            subscriptions=subs,
            churned_count=1,
            marketing_sales_spend=3000.0,
            new_subscribers_count=2,
            gross_margin_pct=80.0,
        )
        assert saas.mrr == 600.0  # 500 + 100
        assert saas.arr == 7200.0
        assert saas.active_subscribers == 2
        assert saas.arpu == 300.0
        assert saas.cac == 1500.0  # 3000 / 2
        assert saas.churn_rate_pct == 33.33333333333333  # 1 / (2+1) * 100

    def test_calculate_growth_metrics(self):
        growth = KPICalculator.calculate_growth(
            current_revenue=120000.0,
            prior_month_revenue=100000.0,
            prior_year_revenue=80000.0,
            current_expense=40000.0,
            prior_month_expense=35000.0,
            current_net_margin_pct=30.0,
            prior_net_margin_pct=25.0,
        )
        assert growth.mom_revenue_growth_pct == 20.0  # (120k - 100k) / 100k * 100
        assert growth.yoy_revenue_growth_pct == 50.0  # (120k - 80k) / 80k * 100
        assert round(growth.mom_expense_growth_pct, 2) == 14.29
        assert growth.net_margin_change_bps == 500.0  # (30 - 25) * 100

    def test_kpi_summary_serialization(self):
        fin = KPICalculator.calculate_financials(100.0, 20.0, 30.0, 5.0, 0.0, 1000.0, 100.0, 30.0)
        summary = KPISummary(financials=fin, currency="EUR", tenant_id="tenant_123")
        s_dict = summary.to_dict()
        assert s_dict["metadata"]["currency"] == "EUR"
        assert s_dict["metadata"]["tenant_id"] == "tenant_123"
        assert s_dict["financials"]["gross_revenue"] == 100.0
