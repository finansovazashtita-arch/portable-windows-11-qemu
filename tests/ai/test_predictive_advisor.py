"""
Unit tests for Predictive AI Advisory & Autonomous Decision Engine (M77).
"""

import json
import unittest

from src.ai.predictive_advisor import (
    AccountingJournalAdvice,
    AdvisoryCategory,
    AdvisoryInsight,
    AdvisoryUrgency,
    CashConversionCycleBreakdown,
    PredictiveAIAdvisor,
    ScenarioForecastPoint,
    ScenarioSimulationResult,
    ScenarioType,
    TaxOptimizationStrategy,
)


class TestPredictiveAIAdvisor(unittest.TestCase):
    """Test suite for PredictiveAIAdvisor core engine."""

    def setUp(self):
        self.advisor = PredictiveAIAdvisor(seed=42)
        self.tenant_id = "tenant-test-77"
        self.sample_financial_summary = {
            "cash_balance_bgn": 50000.0,
            "monthly_revenue_bgn": 90000.0,
            "monthly_expenses_bgn": 105000.0,  # Negative cash flow (-15k/mo), runway 3.33 months (< 6)
            "accounts_receivable_bgn": 85000.0,
            "accounts_payable_bgn": 50000.0,
            "inventory_bgn": 40000.0,
            "total_assets_bgn": 300000.0,
            "total_liabilities_bgn": 210000.0,  # High debt
            "retained_earnings_bgn": 50000.0,
            "annual_revenue_bgn": 1080000.0,
            "ytd_revenue_bgn": 85000.0,
            "forecasted_annual_profit_bgn": 60000.0,
        }

    def test_generate_advisory_insights_all(self):
        insights = self.advisor.generate_advisory_insights(
            tenant_id=self.tenant_id,
            financial_summary=self.sample_financial_summary,
        )
        self.assertGreater(len(insights), 0)

        # Check critical liquidity alert was generated due to negative net cash flow and short runway
        liq_insights = [i for i in insights if i.category == AdvisoryCategory.LIQUIDITY]
        self.assertTrue(len(liq_insights) > 0)
        self.assertEqual(liq_insights[0].urgency, AdvisoryUrgency.CRITICAL)
        self.assertIsNotNone(liq_insights[0].journal_advice)
        self.assertEqual(liq_insights[0].journal_advice.debit_account, "503")

    def test_generate_advisory_insights_filtering(self):
        insights_tax = self.advisor.generate_advisory_insights(
            tenant_id=self.tenant_id,
            financial_summary=self.sample_financial_summary,
            filter_category="TAX_OPTIMIZATION",
        )
        for ins in insights_tax:
            self.assertEqual(ins.category.value, "TAX_OPTIMIZATION")

        insights_critical = self.advisor.generate_advisory_insights(
            tenant_id=self.tenant_id,
            financial_summary=self.sample_financial_summary,
            filter_urgency="CRITICAL",
        )
        for ins in insights_critical:
            self.assertEqual(ins.urgency.value, "CRITICAL")

    def test_simulate_scenarios(self):
        sim = self.advisor.simulate_scenarios(
            tenant_id=self.tenant_id,
            financial_summary=self.sample_financial_summary,
            horizon_days=90,
        )
        self.assertIsInstance(sim, ScenarioSimulationResult)
        self.assertEqual(sim.horizon_days, 90)
        self.assertIn("BASE_CASE", sim.scenarios)
        self.assertIn("OPTIMISTIC", sim.scenarios)
        self.assertIn("DOWNTURN", sim.scenarios)
        self.assertIn("EXPANSION", sim.scenarios)

        base_pt = sim.scenarios["BASE_CASE"][-1]
        self.assertIsInstance(base_pt, ScenarioForecastPoint)
        self.assertGreater(len(sim.key_findings), 0)

    def test_calculate_cash_conversion_cycle(self):
        ccc = self.advisor.calculate_cash_conversion_cycle(
            tenant_id=self.tenant_id,
            financial_summary=self.sample_financial_summary,
        )
        self.assertIsInstance(ccc, CashConversionCycleBreakdown)
        self.assertGreater(ccc.dso_days, 0)
        self.assertGreater(ccc.dpo_days, 0)
        self.assertGreater(ccc.dio_days, 0)
        self.assertEqual(round(ccc.dso_days + ccc.dio_days - ccc.dpo_days, 1), ccc.ccc_days)
        self.assertGreater(len(ccc.recommendations), 0)

    def test_evaluate_tax_strategy(self):
        tax_strat = self.advisor.evaluate_tax_strategy(
            tenant_id=self.tenant_id,
            financial_summary=self.sample_financial_summary,
        )
        self.assertIsInstance(tax_strat, TaxOptimizationStrategy)
        self.assertEqual(tax_strat.vat_threshold_bgn, 100000.0)
        self.assertEqual(tax_strat.estimated_corporate_tax_cita_bgn, 6000.0)  # 10% of 60,000
        self.assertIn("recommended_payout_bgn", tax_strat.dividend_tax_optimization)
        self.assertGreater(len(tax_strat.recommended_provisions), 0)

    def test_altman_z_score_calculation(self):
        z_safe = PredictiveAIAdvisor.calculate_altman_z_score(
            working_capital=100000.0,
            total_assets=300000.0,
            retained_earnings=80000.0,
            ebit=50000.0,
            market_value_equity=200000.0,
            total_liabilities=100000.0,
            sales=400000.0,
        )
        self.assertGreater(z_safe, 2.0)


if __name__ == "__main__":
    unittest.main()
