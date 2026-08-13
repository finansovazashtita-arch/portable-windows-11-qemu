"""
REST API Router & Handlers for Predictive AI Advisory (M77).

Exposes RESTful endpoints for advisory insights, scenario simulations,
Cash Conversion Cycle (CCC) optimization, tax strategies, and report exporting.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from src.ai.predictive_advisor import PredictiveAIAdvisor

logger = logging.getLogger("advisory_api")
ADVISOR_ENGINE = PredictiveAIAdvisor(seed=42)


def get_advisory_insights_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles GET /api/v1/advisory/insights requests.
    """
    tenant_id = params.get("tenant_id", "tenant-demo-001")
    category = params.get("category")
    urgency = params.get("urgency")

    # Sample/live financial summary lookup
    financial_summary = params.get("financial_summary") or {
        "cash_balance_bgn": float(params.get("cash_balance_bgn", 145000.0)),
        "monthly_revenue_bgn": float(params.get("monthly_revenue_bgn", 88000.0)),
        "monthly_expenses_bgn": float(params.get("monthly_expenses_bgn", 92000.0)),  # slight net burn for demo
        "accounts_receivable_bgn": float(params.get("accounts_receivable_bgn", 78000.0)),
        "accounts_payable_bgn": float(params.get("accounts_payable_bgn", 45000.0)),
        "inventory_bgn": float(params.get("inventory_bgn", 32000.0)),
        "total_assets_bgn": float(params.get("total_assets_bgn", 320000.0)),
        "total_liabilities_bgn": float(params.get("total_liabilities_bgn", 180000.0)),
        "retained_earnings_bgn": float(params.get("retained_earnings_bgn", 65000.0)),
        "annual_revenue_bgn": float(params.get("annual_revenue_bgn", 1056000.0)),
    }

    insights = ADVISOR_ENGINE.generate_advisory_insights(
        tenant_id=tenant_id,
        financial_summary=financial_summary,
        filter_category=category,
        filter_urgency=urgency,
    )

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "total_insights": len(insights),
        "insights": [i.to_dict() for i in insights],
    }


def run_scenario_simulation_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles POST /api/v1/advisory/scenarios requests.
    """
    tenant_id = payload.get("tenant_id", "tenant-demo-001")
    horizon_days = int(payload.get("horizon_days", 90))
    custom_params = payload.get("custom_params", {})
    financial_summary = payload.get("financial_summary") or {
        "cash_balance_bgn": float(payload.get("cash_balance_bgn", 145000.0)),
        "monthly_revenue_bgn": float(payload.get("monthly_revenue_bgn", 88000.0)),
        "monthly_expenses_bgn": float(payload.get("monthly_expenses_bgn", 75000.0)),
        "total_assets_bgn": float(payload.get("total_assets_bgn", 350000.0)),
        "total_liabilities_bgn": float(payload.get("total_liabilities_bgn", 120000.0)),
    }

    sim_res = ADVISOR_ENGINE.simulate_scenarios(
        tenant_id=tenant_id,
        financial_summary=financial_summary,
        horizon_days=horizon_days,
        custom_params=custom_params,
    )

    return {
        "status": "success",
        "simulation": sim_res.to_dict(),
    }


def get_cash_conversion_cycle_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles GET /api/v1/advisory/cash-conversion-cycle requests.
    """
    tenant_id = params.get("tenant_id", "tenant-demo-001")
    financial_summary = params.get("financial_summary") or {
        "accounts_receivable_bgn": float(params.get("accounts_receivable_bgn", 78000.0)),
        "accounts_payable_bgn": float(params.get("accounts_payable_bgn", 45000.0)),
        "inventory_bgn": float(params.get("inventory_bgn", 32000.0)),
        "annual_revenue_bgn": float(params.get("annual_revenue_bgn", 1056000.0)),
        "annual_cogs_bgn": float(params.get("annual_cogs_bgn", 686400.0)),
    }

    ccc_res = ADVISOR_ENGINE.calculate_cash_conversion_cycle(
        tenant_id=tenant_id,
        financial_summary=financial_summary,
    )

    return {
        "status": "success",
        "cash_conversion_cycle": ccc_res.to_dict(),
    }


def get_tax_strategy_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles GET /api/v1/advisory/tax-strategy requests.
    """
    tenant_id = params.get("tenant_id", "tenant-demo-001")
    financial_summary = params.get("financial_summary") or {
        "ytd_revenue_bgn": float(params.get("ytd_revenue_bgn", 82000.0)),
        "monthly_revenue_bgn": float(params.get("monthly_revenue_bgn", 18000.0)),
        "forecasted_annual_profit_bgn": float(params.get("forecasted_annual_profit_bgn", 55000.0)),
        "retained_earnings_bgn": float(params.get("retained_earnings_bgn", 75000.0)),
    }

    tax_res = ADVISOR_ENGINE.evaluate_tax_strategy(
        tenant_id=tenant_id,
        financial_summary=financial_summary,
    )

    return {
        "status": "success",
        "tax_strategy": tax_res.to_dict(),
    }


def export_advisory_report_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles POST /api/v1/advisory/export requests.
    Exports advisory brief in JSON, CSV, or PDF summary format.
    """
    tenant_id = payload.get("tenant_id", "tenant-demo-001")
    format_type = payload.get("format", "JSON").upper()

    # Generate complete advisory payload
    insights_res = get_advisory_insights_handler({"tenant_id": tenant_id})
    scenarios_res = run_scenario_simulation_handler({"tenant_id": tenant_id, "horizon_days": 90})
    ccc_res = get_cash_conversion_cycle_handler({"tenant_id": tenant_id})
    tax_res = get_tax_strategy_handler({"tenant_id": tenant_id})

    report_content = {
        "tenant_id": tenant_id,
        "export_format": format_type,
        "executive_summary": {
            "total_insights": insights_res["total_insights"],
            "ccc_days": ccc_res["cash_conversion_cycle"]["ccc_days"],
            "estimated_cita_tax_bgn": tax_res["tax_strategy"]["estimated_corporate_tax_cita_bgn"],
            "base_case_ending_cash_bgn": scenarios_res["simulation"]["metrics_summary"]["BASE_CASE"]["ending_cash_bgn"],
        },
        "insights": insights_res["insights"],
        "scenarios": scenarios_res["simulation"],
        "cash_conversion_cycle": ccc_res["cash_conversion_cycle"],
        "tax_strategy": tax_res["tax_strategy"],
    }

    if format_type == "CSV":
        # Format insights as CSV lines
        csv_lines = ["id,tenant_id,title,category,urgency,impact_bgn,confidence"]
        for ins in insights_res["insights"]:
            csv_lines.append(
                f"{ins['insight_id']},{ins['tenant_id']},\"{ins['title']}\",{ins['category']},{ins['urgency']},{ins['financial_impact_bgn']},{ins['confidence_score']}"
            )
        return {
            "status": "success",
            "format": "CSV",
            "filename": f"advisory_report_{tenant_id}.csv",
            "content": "\n".join(csv_lines),
        }
    elif format_type == "PDF":
        return {
            "status": "success",
            "format": "PDF",
            "filename": f"advisory_report_{tenant_id}.pdf",
            "pdf_summary": report_content["executive_summary"],
            "raw_payload": report_content,
        }
    else:
        return {
            "status": "success",
            "format": "JSON",
            "filename": f"advisory_report_{tenant_id}.json",
            "content": report_content,
        }
