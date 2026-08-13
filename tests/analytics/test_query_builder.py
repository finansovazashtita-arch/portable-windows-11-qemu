"""
Unit Tests for Analytics Query Builder & OLAP Engine (Milestone M76).
"""

import pytest
from src.analytics.query_builder import AnalyticsQueryBuilder, QueryFilter, AggregationMetric


class TestAnalyticsQueryBuilder:

    @pytest.fixture
    def sample_data(self):
        return [
            {"date": "2026-01-10", "tenant_id": "t1", "counterparty": "Company A", "account_code": "702", "amount": 1000.0, "category": "Sales"},
            {"date": "2026-01-15", "tenant_id": "t1", "counterparty": "Company B", "account_code": "602", "amount": 400.0, "category": "Services"},
            {"date": "2026-02-10", "tenant_id": "t1", "counterparty": "Company A", "account_code": "702", "amount": 1500.0, "category": "Sales"},
            {"date": "2026-02-20", "tenant_id": "t2", "counterparty": "Company C", "account_code": "702", "amount": 2000.0, "category": "Sales"},
        ]

    def test_query_filter_date_and_tenant(self, sample_data):
        qb = AnalyticsQueryBuilder(sample_data)
        q_filter = QueryFilter(start_date="2026-01-01", end_date="2026-01-31", tenant_id="t1")
        res = qb.execute_query(filters=q_filter)
        assert res.total_records == 1
        assert res.data[0]["sum_amount"] == 1400.0

    def test_query_group_by_counterparty(self, sample_data):
        qb = AnalyticsQueryBuilder(sample_data)
        metrics = [{"field": "amount", "agg": AggregationMetric.SUM, "alias": "total_amount"}]
        res = qb.execute_query(group_by=["counterparty"], metrics=metrics, order_by="total_amount", ascending=False)
        assert len(res.data) == 3
        # Company A has 1000 + 1500 = 2500
        assert res.data[0]["counterparty"] == "Company A"
        assert res.data[0]["total_amount"] == 2500.0

    def test_query_group_by_period(self, sample_data):
        qb = AnalyticsQueryBuilder(sample_data)
        metrics = [
            {"field": "amount", "agg": AggregationMetric.SUM, "alias": "sum_amount"},
            {"field": "amount", "agg": AggregationMetric.AVG, "alias": "avg_amount"},
        ]
        res = qb.execute_query(group_by=["period"], metrics=metrics, order_by="period", ascending=True)
        assert len(res.data) == 2
        assert res.data[0]["period"] == "2026-01"
        assert res.data[0]["sum_amount"] == 1400.0
        assert res.data[0]["avg_amount"] == 700.0

    def test_query_pagination(self, sample_data):
        qb = AnalyticsQueryBuilder(sample_data)
        res = qb.execute_query(group_by=["counterparty"], limit=2, offset=0)
        assert len(res.data) == 2
        assert res.total_records == 3
