"""
Unit Tests for BI Report Exporter (Milestone M76).
"""

import json
import pytest
from src.analytics.exporter import BIReportExporter, ExportFormat
from src.analytics.kpi_calculator import KPICalculator, KPISummary
from src.analytics.query_builder import AnalyticsQueryBuilder, QueryResult


class TestBIReportExporter:

    @pytest.fixture
    def sample_query_result(self):
        return QueryResult(
            dimensions=["period"],
            metrics=["sum_amount"],
            data=[{"period": "2026-01", "sum_amount": 12000.0}],
            total_records=1,
            summary_totals={"sum_amount": 12000.0},
        )

    def test_export_query_result_json(self, sample_query_result):
        data_bytes = BIReportExporter.export_query_result(sample_query_result, ExportFormat.JSON)
        payload = json.loads(data_bytes.decode("utf-8"))
        assert payload["total_records"] == 1
        assert payload["data"][0]["period"] == "2026-01"

    def test_export_query_result_csv(self, sample_query_result):
        data_bytes = BIReportExporter.export_query_result(sample_query_result, ExportFormat.CSV)
        text = data_bytes.decode("utf-8")
        assert "period,sum_amount" in text
        assert "2026-01,12000.0" in text

    def test_export_query_result_html(self, sample_query_result):
        data_bytes = BIReportExporter.export_query_result(sample_query_result, ExportFormat.HTML)
        text = data_bytes.decode("utf-8")
        assert "<html>" in text
        assert "FinansProtect BI Aggregation Report" in text
        assert "2026-01" in text

    def test_export_kpi_summary_csv_and_html(self):
        fin = KPICalculator.calculate_financials(50000.0, 10000.0, 15000.0, 2000.0, 0.0, 80000.0, 50000.0, 15000.0)
        summary = KPISummary(financials=fin, currency="EUR", tenant_id="tenant_exp")

        csv_bytes = BIReportExporter.export_kpi_summary(summary, ExportFormat.CSV)
        assert "gross_revenue" in csv_bytes.decode("utf-8")

        html_bytes = BIReportExporter.export_kpi_summary(summary, ExportFormat.HTML)
        assert "FinansProtect Executive BI Summary" in html_bytes.decode("utf-8")
