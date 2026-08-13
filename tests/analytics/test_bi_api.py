"""
Integration Tests for BI Analytics REST API & Dashboard Server (Milestone M76).
"""

import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.analytics.bi_api import analytics_router, global_bi_engine

app = FastAPI()
app.include_router(analytics_router)
client = TestClient(app)


class TestBIAnalyticsAPI:

    def test_get_executive_overview(self):
        res = client.get("/api/v1/analytics/overview?currency=BGN")
        assert res.status_code == 200
        data = res.json()
        assert "financials" in data
        assert "ar_ap" in data
        assert "saas" in data
        assert "growth" in data
        assert data["metadata"]["currency"] == "BGN"

    def test_get_kpis(self):
        res = client.get("/api/v1/analytics/kpis")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "kpis" in data

    def test_post_analytics_query(self):
        payload = {
            "group_by": ["period"],
            "metrics": [{"field": "amount", "agg": "sum", "alias": "sum_amount"}],
            "limit": 10
        }
        res = client.post("/api/v1/analytics/query", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "result" in data
        assert len(data["result"]["data"]) > 0

    def test_get_analytics_trends(self):
        res = client.get("/api/v1/analytics/trends?period_dimension=month")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert isinstance(data["trends"], list)

    def test_post_scenario_simulation(self):
        payload = {
            "revenue_change_pct": 15.0,
            "expense_change_pct": -5.0,
            "subscriber_growth_pct": 25.0
        }
        res = client.post("/api/v1/analytics/scenario", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "simulation" in data
        assert data["simulation"]["scenario"]["revenue_change_pct"] == 15.0

    def test_get_alerts_and_add_rule(self):
        res = client.get("/api/v1/analytics/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "total_active_alerts" in data

        rule_payload = {
            "name": "Test Margin Rule",
            "metric_path": "financials.net_margin_pct",
            "comparator": "<",
            "threshold": 15.0,
            "severity": "HIGH"
        }
        post_res = client.post("/api/v1/analytics/alerts/rules", json=rule_payload)
        assert post_res.status_code == 200
        assert post_res.json()["status"] == "success"

    def test_post_export_report_csv(self):
        payload = {
            "format_type": "csv"
        }
        res = client.post("/api/v1/analytics/export", json=payload)
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert b"financials" in res.content or b"gross_revenue" in res.content
