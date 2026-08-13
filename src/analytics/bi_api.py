"""
BI Analytics REST API Endpoints Module (Milestone M76).

Exposes FastAPI routes for C-level dashboards, dynamic OLAP queries,
threshold alerts, scenario simulations, and report exports.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from src.analytics.bi_engine import BIEngine
from src.analytics.query_builder import QueryFilter, AggregationMetric
from src.analytics.bi_alerts import AlertRule, AlertSeverity
from src.analytics.exporter import ExportFormat

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["BI Analytics Dashboard"])

# Global singleton BI engine instance
global_bi_engine = BIEngine()

# Seed sample transactions for demonstration / testing if empty
_sample_records = [
    {"date": "2026-01-15", "type": "credit", "amount": 45000.0, "counterparty": "TechCorp AD", "account_code": "702", "category": "Sales", "tenant_id": "tenant_prod_1", "currency": "BGN"},
    {"date": "2026-01-20", "type": "debit", "amount": 12000.0, "counterparty": "AWS Cloud", "account_code": "602", "category": "Hosting", "tenant_id": "tenant_prod_1", "currency": "BGN"},
    {"date": "2026-02-10", "type": "credit", "amount": 58000.0, "counterparty": "Global Logistics", "account_code": "702", "category": "Sales", "tenant_id": "tenant_prod_1", "currency": "BGN"},
    {"date": "2026-02-18", "type": "debit", "amount": 15000.0, "counterparty": "Office Lease", "account_code": "602", "category": "Rent", "tenant_id": "tenant_prod_1", "currency": "BGN"},
    {"date": "2026-03-05", "type": "credit", "amount": 62000.0, "counterparty": "TechCorp AD", "account_code": "702", "category": "Sales", "tenant_id": "tenant_prod_1", "currency": "BGN"},
    {"date": "2026-03-22", "type": "debit", "amount": 14000.0, "counterparty": "Salaries Expense", "account_code": "604", "category": "Payroll", "tenant_id": "tenant_prod_1", "currency": "BGN"},
]

_sample_subs = [
    {"tenant_id": "tenant_prod_1", "status": "active", "price": 499.0, "interval": "month", "plan": "Enterprise"},
    {"tenant_id": "tenant_prod_2", "status": "active", "price": 199.0, "interval": "month", "plan": "Professional"},
    {"tenant_id": "tenant_prod_3", "status": "active", "price": 2400.0, "interval": "year", "plan": "Enterprise"},
]

_sample_ar = [
    {"counterparty": "TechCorp AD", "amount": 15000.0, "age_days": 15},
    {"counterparty": "Bulgaria Retail Ltd", "amount": 8500.0, "age_days": 45},
]

_sample_ap = [
    {"counterparty": "AWS Cloud", "amount": 4200.0, "age_days": 10},
    {"counterparty": "Office Lease", "amount": 12000.0, "age_days": 25},
]

global_bi_engine.load_data(
    records=_sample_records,
    subscriptions=_sample_subs,
    ar_items=_sample_ar,
    ap_items=_sample_ap,
)


class QueryRequestPayload(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tenant_id: Optional[str] = None
    counterparties: List[str] = Field(default_factory=list)
    account_codes: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Optional[str] = None
    group_by: List[str] = Field(default_factory=lambda: ["period"])
    metrics: List[Dict[str, str]] = Field(
        default_factory=lambda: [{"field": "amount", "agg": "sum", "alias": "total_amount"}]
    )
    order_by: Optional[str] = None
    ascending: bool = False
    limit: int = 100
    offset: int = 0


class ScenarioSimulationRequest(BaseModel):
    revenue_change_pct: float = 0.0
    expense_change_pct: float = 0.0
    subscriber_growth_pct: float = 0.0
    tenant_id: Optional[str] = None


class AlertRulePayload(BaseModel):
    rule_id: Optional[str] = None
    name: str
    metric_path: str
    comparator: str
    threshold: float
    severity: str = AlertSeverity.MEDIUM
    description: str = ""
    enabled: bool = True
    tenant_id: Optional[str] = None


class ReportExportRequest(BaseModel):
    format_type: str = ExportFormat.CSV
    tenant_id: Optional[str] = None
    query_payload: Optional[QueryRequestPayload] = None


@analytics_router.get("/overview", summary="Executive C-Level BI Summary")
def get_executive_overview(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    currency: str = Query("BGN", description="Target reporting currency"),
    period: str = Query("monthly", description="Reporting period"),
):
    """Retrieve full executive BI summary containing financial, AR/AP, SaaS, and growth KPIs."""
    summary = global_bi_engine.compute_kpi_summary(tenant_id=tenant_id, currency=currency, period=period)
    return summary.to_dict()


@analytics_router.get("/kpis", summary="Detailed BI KPI Matrix")
def get_kpis(tenant_id: Optional[str] = Query(None)):
    """Retrieve high-level financial and operational KPI breakdown."""
    summary = global_bi_engine.compute_kpi_summary(tenant_id=tenant_id)
    return {
        "status": "success",
        "kpis": summary.to_dict(),
    }


@analytics_router.post("/query", summary="Multi-Dimensional OLAP Aggregation Query")
def execute_analytics_query(payload: QueryRequestPayload):
    """Execute dynamic multi-dimensional OLAP queries against transaction datasets."""
    q_filter = QueryFilter(
        start_date=payload.start_date,
        end_date=payload.end_date,
        tenant_id=payload.tenant_id,
        counterparties=payload.counterparties,
        account_codes=payload.account_codes,
        categories=payload.categories,
        min_amount=payload.min_amount,
        max_amount=payload.max_amount,
        currency=payload.currency,
    )

    res = global_bi_engine.execute_olap_query(
        filters=q_filter,
        group_by=payload.group_by,
        metrics=payload.metrics,
        order_by=payload.order_by,
        ascending=payload.ascending,
        limit=payload.limit,
        offset=payload.offset,
    )

    return {
        "status": "success",
        "result": {
            "dimensions": res.dimensions,
            "metrics": res.metrics,
            "summary_totals": res.summary_totals,
            "total_records": res.total_records,
            "data": res.data,
        },
    }


@analytics_router.get("/trends", summary="Time-Series Trend Data for UI Charts")
def get_analytics_trends(
    tenant_id: Optional[str] = Query(None),
    period_dimension: str = Query("month", description="Aggregation period (month, day, year)"),
):
    """Fetch monthly revenue, expense, and net profit time-series for frontend visual charts."""
    q_filter = QueryFilter(tenant_id=tenant_id)
    metrics = [
        {"field": "amount", "agg": AggregationMetric.SUM, "alias": "total_amount"},
        {"field": "amount", "agg": AggregationMetric.COUNT, "alias": "transaction_count"},
    ]
    res = global_bi_engine.execute_olap_query(
        filters=q_filter,
        group_by=[period_dimension],
        metrics=metrics,
        order_by=period_dimension,
        ascending=True,
    )

    # Transform into chart-ready series
    trend_series = []
    for r in res.data:
        trend_series.append({
            "period": r.get(period_dimension, "Unknown"),
            "revenue": r.get("total_amount", 0.0),
            "transactions": int(r.get("transaction_count", 0)),
        })

    return {
        "status": "success",
        "trends": trend_series,
    }


@analytics_router.post("/scenario", summary="Sensitivity Scenario Simulation")
def simulate_scenario(payload: ScenarioSimulationRequest):
    """Run sensitivity analysis projecting changes in revenue, expenses, or SaaS subscribers."""
    summary = global_bi_engine.compute_kpi_summary(tenant_id=payload.tenant_id)
    simulation = global_bi_engine.run_scenario_simulation(
        base_summary=summary,
        revenue_change_pct=payload.revenue_change_pct,
        expense_change_pct=payload.expense_change_pct,
        subscriber_growth_pct=payload.subscriber_growth_pct,
    )
    return {
        "status": "success",
        "simulation": simulation,
    }


@analytics_router.get("/alerts", summary="Active BI Threshold Alerts")
def get_active_alerts(tenant_id: Optional[str] = Query(None)):
    """Retrieve triggered BI threshold alerts."""
    summary = global_bi_engine.compute_kpi_summary(tenant_id=tenant_id)
    alerts = global_bi_engine.alert_manager.get_active_alerts(tenant_id=tenant_id)
    return {
        "status": "success",
        "total_active_alerts": len(alerts),
        "alerts": [
            {
                "alert_id": a.alert_id,
                "rule_id": a.rule_id,
                "rule_name": a.rule_name,
                "metric_path": a.metric_path,
                "actual_value": a.actual_value,
                "threshold": a.threshold,
                "comparator": a.comparator,
                "severity": a.severity,
                "message": a.message,
                "timestamp": a.timestamp,
                "status": a.status,
            }
            for a in alerts
        ],
    }


@analytics_router.post("/alerts/rules", summary="Register or Update Alert Rule")
def add_alert_rule(payload: AlertRulePayload):
    """Add a new threshold alert rule."""
    rule = AlertRule(
        rule_id=payload.rule_id or "",
        name=payload.name,
        metric_path=payload.metric_path,
        comparator=payload.comparator,
        threshold=payload.threshold,
        severity=payload.severity,
        description=payload.description,
        enabled=payload.enabled,
        tenant_id=payload.tenant_id,
    )
    rule_id = global_bi_engine.alert_manager.add_rule(rule)
    return {"status": "success", "rule_id": rule_id, "message": f"Alert rule '{rule.name}' registered."}


@analytics_router.post("/export", summary="Export BI Report or Dataset")
def export_analytics_report(payload: ReportExportRequest):
    """Export executive KPI summary or OLAP query dataset into CSV, JSON, HTML, or XLSX."""
    format_type = payload.format_type.lower()
    media_type = "text/csv"
    if format_type == ExportFormat.JSON:
        media_type = "application/json"
    elif format_type == ExportFormat.HTML:
        media_type = "text/html"
    elif format_type == ExportFormat.XLSX:
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    query_res = None
    if payload.query_payload:
        q_filter = QueryFilter(
            start_date=payload.query_payload.start_date,
            end_date=payload.query_payload.end_date,
            tenant_id=payload.query_payload.tenant_id,
            counterparties=payload.query_payload.counterparties,
            account_codes=payload.query_payload.account_codes,
            categories=payload.query_payload.categories,
            min_amount=payload.query_payload.min_amount,
            max_amount=payload.query_payload.max_amount,
            currency=payload.query_payload.currency,
        )
        query_res = global_bi_engine.execute_olap_query(
            filters=q_filter,
            group_by=payload.query_payload.group_by,
            metrics=payload.query_payload.metrics,
            order_by=payload.query_payload.order_by,
            ascending=payload.query_payload.ascending,
            limit=payload.query_payload.limit,
            offset=payload.query_payload.offset,
        )

    summary = global_bi_engine.compute_kpi_summary(tenant_id=payload.tenant_id)
    content_bytes = global_bi_engine.export_report(
        summary=summary,
        query_result=query_res,
        format_type=format_type,
    )

    filename = f"finansprotect_bi_report.{format_type}"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}

    return Response(content=content_bytes, media_type=media_type, headers=headers)
