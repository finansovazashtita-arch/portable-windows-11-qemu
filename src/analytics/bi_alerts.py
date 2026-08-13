"""
BI Threshold Alerting & Anomaly Engine Module (Milestone M76).

Monitors financial KPIs, liquidity indicators, and multi-tenant performance metrics
against customizable operational threshold rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Dict, List, Any, Optional

from src.analytics.kpi_calculator import KPISummary


class AlertSeverity:
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus:
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


@dataclass
class AlertRule:
    rule_id: str
    name: str
    metric_path: str  # e.g., "financials.net_margin_pct", "financials.cash_runway_months"
    comparator: str  # "<", "<=", ">", ">=", "==", "!="
    threshold: float
    severity: str = AlertSeverity.MEDIUM
    description: str = ""
    enabled: bool = True
    tenant_id: Optional[str] = None


@dataclass
class TriggeredAlert:
    alert_id: str
    rule_id: str
    rule_name: str
    metric_path: str
    actual_value: float
    threshold: float
    comparator: str
    severity: str
    message: str
    timestamp: str
    status: str = AlertStatus.ACTIVE
    tenant_id: Optional[str] = None


class BIAlertManager:
    """Manages threshold rules and evaluates real-time alerts for BI metrics."""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.triggered_alerts: Dict[str, TriggeredAlert] = {}
        self._load_default_rules()

    def _load_default_rules(self):
        """Register default C-level financial health threshold rules."""
        defaults = [
            AlertRule(
                rule_id="default_net_margin_low",
                name="Net Profit Margin Warning",
                metric_path="financials.net_margin_pct",
                comparator="<",
                threshold=10.0,
                severity=AlertSeverity.HIGH,
                description="Triggered when net profit margin falls below 10%.",
            ),
            AlertRule(
                rule_id="default_cash_runway_critical",
                name="Critical Cash Runway Breach",
                metric_path="financials.cash_runway_months",
                comparator="<",
                threshold=3.0,
                severity=AlertSeverity.CRITICAL,
                description="Triggered when cash runway drops below 3 months.",
            ),
            AlertRule(
                rule_id="default_churn_high",
                name="Elevated SaaS Churn Rate",
                metric_path="saas.churn_rate_pct",
                comparator=">",
                threshold=5.0,
                severity=AlertSeverity.MEDIUM,
                description="Triggered when monthly SaaS churn rate exceeds 5%.",
            ),
            AlertRule(
                rule_id="default_expense_spike",
                name="MoM Expense Growth Spike",
                metric_path="growth.mom_expense_growth_pct",
                comparator=">",
                threshold=25.0,
                severity=AlertSeverity.HIGH,
                description="Triggered when operating expenses increase by >25% MoM.",
            ),
            AlertRule(
                rule_id="default_dso_long",
                name="Excessive Days Sales Outstanding (DSO)",
                metric_path="ar_ap.dso_days",
                comparator=">",
                threshold=60.0,
                severity=AlertSeverity.MEDIUM,
                description="Triggered when DSO exceeds 60 days.",
            ),
        ]
        for r in defaults:
            self.rules[r.rule_id] = r

    def add_rule(self, rule: AlertRule) -> str:
        if not rule.rule_id:
            rule.rule_id = f"rule_{uuid.uuid4().hex[:8]}"
        self.rules[rule.rule_id] = rule
        return rule.rule_id

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def evaluate_kpi_summary(self, summary: KPISummary) -> List[TriggeredAlert]:
        """Evaluate registered alert rules against a KPISummary instance."""
        new_alerts = []
        summary_dict = summary.to_dict()

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # Scope tenant if applicable
            if rule.tenant_id and summary.tenant_id and rule.tenant_id != summary.tenant_id:
                continue

            val = self._extract_value_by_path(summary_dict, rule.metric_path)
            if val is None:
                continue

            triggered = self._evaluate_condition(val, rule.comparator, rule.threshold)
            if triggered:
                msg = f"BI Alert '{rule.name}': {rule.metric_path} is {val} (threshold: {rule.comparator} {rule.threshold})"
                alert = TriggeredAlert(
                    alert_id=f"alert_{uuid.uuid4().hex[:10]}",
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    metric_path=rule.metric_path,
                    actual_value=val,
                    threshold=rule.threshold,
                    comparator=rule.comparator,
                    severity=rule.severity,
                    message=msg,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status=AlertStatus.ACTIVE,
                    tenant_id=summary.tenant_id,
                )
                self.triggered_alerts[alert.alert_id] = alert
                new_alerts.append(alert)

        return new_alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        if alert_id in self.triggered_alerts:
            self.triggered_alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        if alert_id in self.triggered_alerts:
            self.triggered_alerts[alert_id].status = AlertStatus.RESOLVED
            return True
        return False

    def get_active_alerts(self, tenant_id: Optional[str] = None) -> List[TriggeredAlert]:
        alerts = [a for a in self.triggered_alerts.values() if a.status == AlertStatus.ACTIVE]
        if tenant_id:
            alerts = [a for a in alerts if a.tenant_id == tenant_id or a.tenant_id is None]
        return alerts

    def _extract_value_by_path(self, data: Dict[str, Any], path: str) -> Optional[float]:
        parts = path.split(".")
        curr = data
        for p in parts:
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return None
        try:
            return float(curr)
        except (ValueError, TypeError):
            return None

    def _evaluate_condition(self, actual: float, comparator: str, threshold: float) -> bool:
        if comparator == "<":
            return actual < threshold
        elif comparator == "<=":
            return actual <= threshold
        elif comparator == ">":
            return actual > threshold
        elif comparator == ">=":
            return actual >= threshold
        elif comparator == "==":
            return abs(actual - threshold) < 1e-6
        elif comparator == "!=":
            return abs(actual - threshold) >= 1e-6
        return False
