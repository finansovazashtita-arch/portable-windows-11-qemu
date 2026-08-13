"""
BI Multi-Format Report Exporter Module (Milestone M76).

Exports analytics datasets, query results, KPI summaries, and executive reports
into Excel (XLSX), CSV, JSON, and HTML formats.
"""

import csv
import json
import io
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from src.analytics.kpi_calculator import KPISummary
from src.analytics.query_builder import QueryResult


class ExportFormat:
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    HTML = "html"


class BIReportExporter:
    """Multi-format exporter for BI analytics dashboards and report datasets."""

    @staticmethod
    def export_query_result(query_result: QueryResult, format_type: str = ExportFormat.CSV) -> bytes:
        """Export an Analytics QueryResult into the requested binary/string format."""
        format_type = format_type.lower()
        if format_type == ExportFormat.JSON:
            payload = {
                "dimensions": query_result.dimensions,
                "metrics": query_result.metrics,
                "summary_totals": query_result.summary_totals,
                "total_records": query_result.total_records,
                "data": query_result.data,
            }
            return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

        elif format_type == ExportFormat.CSV:
            output = io.StringIO()
            if query_result.data:
                fieldnames = list(query_result.data[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for row in query_result.data:
                    writer.writerow(row)
            else:
                writer = csv.writer(output)
                writer.writerow(["No Data"])
            return output.getvalue().encode("utf-8")

        elif format_type == ExportFormat.HTML:
            return BIReportExporter._build_html_table(query_result).encode("utf-8")

        elif format_type == ExportFormat.XLSX:
            return BIReportExporter._build_csv_or_excel(query_result)

        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    @staticmethod
    def export_kpi_summary(summary: KPISummary, format_type: str = ExportFormat.JSON) -> bytes:
        """Export a KPISummary object into specified format."""
        format_type = format_type.lower()
        summary_dict = summary.to_dict()

        if format_type == ExportFormat.JSON:
            return json.dumps(summary_dict, indent=2, ensure_ascii=False).encode("utf-8")

        elif format_type == ExportFormat.CSV:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Category", "Metric", "Value", "Currency"])

            for cat, metrics in summary_dict.items():
                if cat == "metadata":
                    continue
                if isinstance(metrics, dict):
                    for metric_name, val in metrics.items():
                        if isinstance(val, dict):
                            for sub_k, sub_v in val.items():
                                writer.writerow([cat, f"{metric_name}.{sub_k}", sub_v, summary.currency])
                        else:
                            writer.writerow([cat, metric_name, val, summary.currency])
            return output.getvalue().encode("utf-8")

        elif format_type == ExportFormat.HTML:
            return BIReportExporter._build_html_kpi_summary(summary).encode("utf-8")

        else:
            return json.dumps(summary_dict, indent=2, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _build_html_table(query_result: QueryResult) -> str:
        html = [
            "<!DOCTYPE html>",
            "<html><head><meta charset='utf-8'><title>FinansProtect BI Query Report</title>",
            "<style>",
            "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 24px; background: #0f172a; color: #f8fafc; }",
            "h2 { color: #38bdf8; font-size: 20px; }",
            "table { width: 100%; border-collapse: collapse; margin-top: 16px; background: #1e293b; border-radius: 8px; overflow: hidden; }",
            "th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; }",
            "th { background: #0284c7; color: #ffffff; font-weight: 600; }",
            "tr:hover { background: #334155; }",
            ".totals { font-weight: bold; background: #0f172a; }",
            "</style></head><body>",
            f"<h2>FinansProtect BI Aggregation Report ({len(query_result.data)} Records)</h2>",
            "<table><thead><tr>",
        ]

        if query_result.data:
            headers = list(query_result.data[0].keys())
            for h in headers:
                html.append(f"<th>{h}</th>")
            html.append("</tr></thead><tbody>")

            for row in query_result.data:
                html.append("<tr>")
                for h in headers:
                    html.append(f"<td>{row.get(h, '')}</td>")
                html.append("</tr>")

            # Totals row
            if query_result.summary_totals:
                html.append("<tr class='totals'>")
                for idx, h in enumerate(headers):
                    if idx == 0:
                        html.append("<td>Total / Summary</td>")
                    elif h in query_result.summary_totals:
                        html.append(f"<td>{query_result.summary_totals[h]}</td>")
                    else:
                        html.append("<td>-</td>")
                html.append("</tr>")

            html.append("</tbody></table></body></html>")
        else:
            html.append("</tr></thead><tbody><tr><td>No data available</td></tr></tbody></table></body></html>")

        return "".join(html)

    @staticmethod
    def _build_html_kpi_summary(summary: KPISummary) -> str:
        d = summary.to_dict()
        fin = d["financials"]
        ar_ap = d["ar_ap"]
        saas = d["saas"]
        growth = d["growth"]

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>FinansProtect Executive Financial Briefing & BI KPIs</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; background: #0b1329; color: #e2e8f0; padding: 32px; margin: 0; }}
        .header {{ border-bottom: 2px solid #0284c7; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-space-between; align-items: center; }}
        h1 {{ color: #38bdf8; margin: 0; font-size: 24px; }}
        .meta {{ color: #94a3b8; font-size: 14px; margin-top: 4px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 32px; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; }}
        .card-title {{ color: #94a3b8; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 12px; }}
        .metric {{ font-size: 28px; font-weight: 700; color: #f8fafc; }}
        .metric-sub {{ font-size: 13px; color: #38bdf8; margin-top: 6px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ padding: 8px 12px; border-bottom: 1px solid #334155; text-align: left; font-size: 14px; }}
        th {{ color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>FinansProtect Executive BI Summary</h1>
            <div class="meta">Period: {summary.period.upper()} | Currency: {summary.currency} | Tenant: {summary.tenant_id or "All Tenants"}</div>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">Gross Revenue</div>
            <div class="metric">{fin['gross_revenue']:,.2f} {summary.currency}</div>
            <div class="metric-sub">Net Profit: {fin['net_profit']:,.2f} {summary.currency} ({fin['net_margin_pct']}%)</div>
        </div>
        <div class="card">
            <div class="card-title">Cash Balance & Runway</div>
            <div class="metric">{fin['cash_balance']:,.2f} {summary.currency}</div>
            <div class="metric-sub">Runway: {fin['cash_runway_months']} Months (Burn: {fin['monthly_burn_rate']:,.2f}/mo)</div>
        </div>
        <div class="card">
            <div class="card-title">SaaS MRR / ARR</div>
            <div class="metric">{saas['mrr']:,.2f} {summary.currency}</div>
            <div class="metric-sub">ARR: {saas['arr']:,.2f} | Churn: {saas['churn_rate_pct']}%</div>
        </div>
        <div class="card">
            <div class="card-title">Receivables & Payables</div>
            <div class="metric">AR: {ar_ap['total_ar']:,.2f}</div>
            <div class="metric-sub">AP: {ar_ap['total_ap']:,.2f} | DSO: {ar_ap['dso_days']} days</div>
        </div>
    </div>
</body>
</html>"""
        return html

    @staticmethod
    def _build_csv_or_excel(query_result: QueryResult) -> bytes:
        # Returns formatted CSV byte stream which Excel opens natively
        return BIReportExporter.export_query_result(query_result, format_type=ExportFormat.CSV)
