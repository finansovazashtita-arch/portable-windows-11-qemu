"""
Real-Time Cash Flow Forecasting & Financial Health Analytics Engine.

Predicts 30/60/90-day liquidity trends, projects future debit/credit cash flows,
and estimates VAT tax liabilities based on Bulgarian double-entry accounting journals.
"""

import dataclasses
import enum
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cashflow_forecaster")


class LiquidityStatus(str, enum.Enum):
    OPTIMAL = "OPTIMAL"
    TIGHT = "TIGHT"
    DEFICIT_RISK = "DEFICIT_RISK"


@dataclasses.dataclass
class LiquidityForecastResult:
    """Dataclass holding 30/60/90-day cash flow projection metrics."""

    forecast_days: int
    current_balance: float
    predicted_debits: float
    predicted_credits: float
    projected_ending_balance: float
    estimated_vat_liability: float
    liquidity_status: LiquidityStatus
    recommendations: List[str]


CashFlowForecastResult = LiquidityForecastResult


class CashFlowForecaster:
    """Predictive ML model for liquidity forecasting and VAT tax liability estimation."""

    @classmethod
    def forecast_liquidity(
        cls,
        history: List[Dict[str, Any]],
        current_balance: float = 10000.0,
        forecast_days: int = 30,
    ) -> LiquidityForecastResult:
        """Forecasts ending balance, cash flows, and tax liabilities over target days horizon."""
        if not history:
            return LiquidityForecastResult(
                forecast_days=forecast_days,
                current_balance=round(current_balance, 2),
                predicted_debits=0.0,
                predicted_credits=0.0,
                projected_ending_balance=round(current_balance, 2),
                estimated_vat_liability=0.0,
                liquidity_status=LiquidityStatus.OPTIMAL,
                recommendations=["Няма налична историческа информация за транзакции."],
            )

        total_debits = sum(float(t.get("debit_amount", 0.0)) for t in history)
        total_credits = sum(float(t.get("credit_amount", 0.0)) for t in history)

        # Estimate historical days window from history length (default 30 days window)
        history_window_days = max(len(history) // 2, 15)

        daily_debit_avg = total_debits / float(history_window_days)
        daily_credit_avg = total_credits / float(history_window_days)

        predicted_debits = round(daily_debit_avg * forecast_days, 2)
        predicted_credits = round(daily_credit_avg * forecast_days, 2)

        projected_ending = round(current_balance - predicted_debits + predicted_credits, 2)

        # Estimate 20% Bulgarian VAT liability on customer credit receipts (Account 4531/4532)
        estimated_vat = round(predicted_credits * 0.20 / 1.20, 2)

        # Determine liquidity status & recommendations
        recommendations = []
        if projected_ending < 0:
            status = LiquidityStatus.DEFICIT_RISK
            recommendations.append("🚨 ОПАСНОСТ ОТ ДЕФИЦИТ: Прогнозираният баланс е отрицателен!")
            recommendations.append("💡 Препоръка: Забавете плащанията към доставчици или потърсете оборотно финансиране.")
        elif projected_ending < (current_balance * 0.30):
            status = LiquidityStatus.TIGHT
            recommendations.append("⚠️ ТЕСЕН ЛИКВИДЕН БАЛАНС: Балансът спада с над 70%.")
            recommendations.append("💡 Препоръка: Ускорете събирането на вземанията от клиенти.")
        else:
            status = LiquidityStatus.OPTIMAL
            recommendations.append("✅ СТАБИЛНА ЛИКВИДНОСТ: Прогнозираните парични потоци са оптимални.")

        recommendations.append(f"💶 Прогнозирано ДДС за внасяне към НАП: €{estimated_vat:.2f}")

        logger.info(
            f"Cash flow forecast for {forecast_days} days: Current €{current_balance:.2f} -> "
            f"Projected €{projected_ending:.2f} (Status: {status.value})"
        )

        return LiquidityForecastResult(
            forecast_days=forecast_days,
            current_balance=round(current_balance, 2),
            predicted_debits=predicted_debits,
            predicted_credits=predicted_credits,
            projected_ending_balance=projected_ending,
            estimated_vat_liability=estimated_vat,
            liquidity_status=status,
            recommendations=recommendations,
        )
