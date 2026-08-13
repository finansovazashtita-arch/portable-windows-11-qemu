"""
Unit Tests for BI Engine & Scenario Simulation (Milestone M76).
"""

import pytest
from src.analytics.bi_engine import BIEngine
from src.analytics.exporter import ExportFormat


class TestBIEngine:

    @pytest.fixture
    def bi_engine(self):
        engine = BIEngine()
        recs = [
            {"date": "2026-01-10", "type": "credit", "amount": 10000.0, "tenant_id": "t1", "category": "Sales"},
            {"date": "2026-01-15", "type": "debit", "amount": 3000.0, "tenant_id": "t1", "category": "Opex"},
            {"date": "2026-02-10", "type": "credit", "amount": 20000.0, "tenant_id": "t1", "category": "Sales"},
        ]
        subs = [
            {"tenant_id": "t1", "status": "active", "price": 500.0, "interval": "month"},
        ]
        engine.load_data(records=recs, subscriptions=subs)
        return engine

    def test_compute_kpi_summary(self, bi_engine):
        summary = bi_engine.compute_kpi_summary(tenant_id="t1")
        assert summary.tenant_id == "t1"
        assert summary.financials.gross_revenue == 30000.0
        assert summary.financials.operating_expenses == 3000.0
        assert summary.saas.mrr == 500.0

    def test_execute_olap_query(self, bi_engine):
        res = bi_engine.execute_olap_query(group_by=["period"], metrics=[{"field": "amount", "agg": "sum"}])
        assert res.total_records == 2
        assert len(res.data) == 2

    def test_run_scenario_simulation(self, bi_engine):
        summary = bi_engine.compute_kpi_summary(tenant_id="t1")
        sim = bi_engine.run_scenario_simulation(
            base_summary=summary,
            revenue_change_pct=20.0,   # +20% revenue
            expense_change_pct=-10.0,  # -10% expenses
            subscriber_growth_pct=50.0,
        )
        assert sim["scenario"]["revenue_change_pct"] == 20.0
        assert sim["simulated"]["net_profit"] > sim["baseline"]["net_profit"]
        assert sim["simulated"]["mrr"] == 750.0

    def test_export_report(self, bi_engine):
        csv_bytes = bi_engine.export_report(format_type=ExportFormat.CSV)
        assert len(csv_bytes) > 0
        assert b"financials" in csv_bytes or b"gross_revenue" in csv_bytes
