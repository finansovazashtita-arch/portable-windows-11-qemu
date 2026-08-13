"""
FinansProtect BI Analytics Module (Milestone M76).

Provides executive C-level dashboards, multi-dimensional OLAP query engines,
financial and operational KPI calculations, threshold alerting, report exporting,
and REST API handlers.
"""

from src.analytics.kpi_calculator import KPICalculator, KPISummary
from src.analytics.query_builder import AnalyticsQueryBuilder, QueryFilter, AggregationMetric
from src.analytics.bi_alerts import BIAlertManager, AlertRule, TriggeredAlert
from src.analytics.exporter import BIReportExporter
from src.analytics.bi_engine import BIEngine
from src.analytics.bi_api import analytics_router

__all__ = [
    "BIEngine",
    "KPICalculator",
    "KPISummary",
    "AnalyticsQueryBuilder",
    "QueryFilter",
    "AggregationMetric",
    "BIAlertManager",
    "AlertRule",
    "TriggeredAlert",
    "BIReportExporter",
    "analytics_router",
]
