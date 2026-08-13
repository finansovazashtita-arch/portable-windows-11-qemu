"""
Unit Tests for BI Alert Threshold & Anomaly Engine (Milestone M76).
"""

import pytest
from src.analytics.bi_alerts import BIAlertManager, AlertRule, AlertSeverity, AlertStatus
from src.analytics.kpi_calculator import KPICalculator, KPISummary


class TestBIAlertManager:

    def test_default_rules_loaded(self):
        mgr = BIAlertManager()
        assert len(mgr.rules) >= 4
        assert "default_net_margin_low" in mgr.rules
        assert "default_cash_runway_critical" in mgr.rules

    def test_evaluate_kpi_summary_triggers_alerts(self):
        mgr = BIAlertManager()
        fin = KPICalculator.calculate_financials(
            gross_revenue=10000.0,
            cost_of_goods_sold=2000.0,
            operating_expenses=7500.0,  # Net margin = (500 / 10000) = 5% (< 10% threshold)
            tax_expenses=0.0,
            depreciation_amortization=0.0,
            cash_balance=10000.0,
            cash_inflows=10000.0,
            cash_outflows=15000.0,  # Burn = 5000/mo -> Runway = 2.0 months (< 3.0 threshold)
        )
        summary = KPISummary(financials=fin, tenant_id="tenant_alert_test")
        alerts = mgr.evaluate_kpi_summary(summary)
        assert len(alerts) >= 2

        rule_ids = [a.rule_id for a in alerts]
        assert "default_net_margin_low" in rule_ids
        assert "default_cash_runway_critical" in rule_ids

    def test_add_and_remove_rule(self):
        mgr = BIAlertManager()
        custom_rule = AlertRule(
            rule_id="custom_rule_1",
            name="Custom Revenue Rule",
            metric_path="financials.gross_revenue",
            comparator="<",
            threshold=50000.0,
        )
        rule_id = mgr.add_rule(custom_rule)
        assert rule_id == "custom_rule_1"
        assert "custom_rule_1" in mgr.rules

        assert mgr.remove_rule("custom_rule_1") is True
        assert "custom_rule_1" not in mgr.rules

    def test_acknowledge_and_resolve_alert(self):
        mgr = BIAlertManager()
        fin = KPICalculator.calculate_financials(100.0, 10.0, 95.0, 0.0, 0.0, 100.0, 100.0, 200.0)
        summary = KPISummary(financials=fin)
        alerts = mgr.evaluate_kpi_summary(summary)
        assert len(alerts) > 0

        alert_id = alerts[0].alert_id
        assert mgr.acknowledge_alert(alert_id) is True
        assert mgr.triggered_alerts[alert_id].status == AlertStatus.ACKNOWLEDGED

        assert mgr.resolve_alert(alert_id) is True
        assert mgr.triggered_alerts[alert_id].status == AlertStatus.RESOLVED
        assert len(mgr.get_active_alerts()) < len(alerts)
