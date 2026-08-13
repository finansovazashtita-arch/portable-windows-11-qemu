"""
Unit tests for Automated Corporate Financial Ratio & Solvency Analyzer Engine.
"""

import unittest

from src.ai.financial_solvency_analyzer import CorporateSolvencyAnalyzer, SolvencyRiskLevel


class TestCorporateSolvencyAnalyzer(unittest.TestCase):
    """Test suite for CorporateSolvencyAnalyzer."""

    def test_safe_zone_analysis(self):
        report = CorporateSolvencyAnalyzer.analyze_financial_health(
            current_assets=150000.0,
            current_liabilities=50000.0,
            cash_and_equiv=40000.0,
            total_assets=300000.0,
            retained_earnings=100000.0,
            ebit=60000.0,
            equity=200000.0,
            total_liabilities=100000.0,
            sales=400000.0,
        )

        self.assertEqual(report.current_ratio, 3.0)
        self.assertEqual(report.cash_ratio, 0.8)
        self.assertGreaterEqual(report.altman_z_score, 2.99)
        self.assertEqual(report.risk_level, SolvencyRiskLevel.SAFE_ZONE)

    def test_distress_zone_analysis(self):
        report = CorporateSolvencyAnalyzer.analyze_financial_health(
            current_assets=20000.0,
            current_liabilities=80000.0,
            cash_and_equiv=5000.0,
            total_assets=100000.0,
            retained_earnings=-20000.0,
            ebit=-10000.0,
            equity=10000.0,
            total_liabilities=90000.0,
            sales=50000.0,
        )

        self.assertLess(report.current_ratio, 1.0)
        self.assertLess(report.altman_z_score, 1.81)
        self.assertEqual(report.risk_level, SolvencyRiskLevel.DISTRESS_ZONE)


if __name__ == "__main__":
    unittest.main()
