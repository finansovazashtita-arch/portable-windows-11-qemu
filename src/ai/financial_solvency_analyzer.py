"""
Automated Corporate Financial Ratio & Solvency Analyzer Engine (Altman Z-Score & Liquidity).

Calculates key corporate financial indicators:
- Current, Quick, and Cash Liquidity Ratios
- Altman Z-Score 5-Factor Corporate Distress Model:
  Z = 1.2(X1) + 1.4(X2) + 3.3(X3) + 0.6(X4) + 0.999(X5)
- Automated Bulgarian financial health recommendations
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("financial_solvency_analyzer")


class SolvencyRiskLevel(str, enum.Enum):
    SAFE_ZONE = "SAFE_ZONE"
    GREY_ZONE = "GREY_ZONE"
    DISTRESS_ZONE = "DISTRESS_ZONE"


@dataclasses.dataclass
class FinancialAnalysisReport:
    """Dataclass holding corporate financial health analysis metrics."""

    current_ratio: float
    quick_ratio: float
    cash_ratio: float
    altman_z_score: float
    risk_level: SolvencyRiskLevel
    recommendation_bg: str


FinancialSolvencyReport = FinancialAnalysisReport


class CorporateSolvencyAnalyzer:
    """Analyzer calculating liquidity ratios and Altman Z-Score solvency indicators."""

    @classmethod
    def analyze_financial_health(
        cls,
        current_assets: float,
        current_liabilities: float,
        cash_and_equiv: float,
        total_assets: float,
        retained_earnings: float,
        ebit: float,
        equity: float,
        total_liabilities: float,
        sales: float,
        inventory: float = 0.0,
        receivables: float = 0.0,
    ) -> FinancialAnalysisReport:
        """Calculates financial ratios and evaluates corporate solvency risk."""
        cl = current_liabilities if current_liabilities > 0 else 1.0
        ta = total_assets if total_assets > 0 else 1.0
        tl = total_liabilities if total_liabilities > 0 else 1.0

        current_ratio = round(current_assets / cl, 2)
        quick_ratio = round((cash_and_equiv + receivables) / cl, 2)
        cash_ratio = round(cash_and_equiv / cl, 2)

        # Altman Z-Score components
        x1 = (current_assets - current_liabilities) / ta  # Working Capital / Total Assets
        x2 = retained_earnings / ta  # Retained Earnings / Total Assets
        x3 = ebit / ta  # EBIT / Total Assets
        x4 = equity / tl  # Equity / Total Liabilities
        x5 = sales / ta  # Sales / Total Assets

        z_score = round(1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5, 2)

        if z_score >= 2.99:
            risk = SolvencyRiskLevel.SAFE_ZONE
            rec = "Отлично финансово здраве. Фирмата е в безопасна зона с нисък риск от фалит."
        elif z_score >= 1.81:
            risk = SolvencyRiskLevel.GREY_ZONE
            rec = "Умерена платежоспособност (Сива зона). Препоръчва се оптимизация на оборотния капитал."
        else:
            risk = SolvencyRiskLevel.DISTRESS_ZONE
            rec = "Внимание: Висок риск от финансови затруднения (Червена зона). Изисква незабавни мерки."

        report = FinancialAnalysisReport(
            current_ratio=current_ratio,
            quick_ratio=quick_ratio,
            cash_ratio=cash_ratio,
            altman_z_score=z_score,
            risk_level=risk,
            recommendation_bg=rec,
        )
        logger.info(f"📊 Corporate Solvency Analysis: Altman Z-Score = {z_score} ({risk.value})")
        return report
