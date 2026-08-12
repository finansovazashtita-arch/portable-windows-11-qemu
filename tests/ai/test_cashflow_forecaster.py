"""
Unit tests for Real-Time Cash Flow Forecasting Engine.
"""

import unittest
from src.ai.cashflow_forecaster import CashFlowForecaster, LiquidityStatus


class TestCashFlowForecaster(unittest.TestCase):
    """Test suite for CashFlowForecaster."""

    def test_forecast_with_empty_history(self):
        res = CashFlowForecaster.forecast_liquidity([], current_balance=5000.0, forecast_days=30)
        self.assertEqual(res.current_balance, 5000.0)
        self.assertEqual(res.projected_ending_balance, 5000.0)
        self.assertEqual(res.liquidity_status, LiquidityStatus.OPTIMAL)

    def test_forecast_optimal_cashflow(self):
        history = [
            {"debit_amount": 100.0, "credit_amount": 500.0},
            {"debit_amount": 200.0, "credit_amount": 600.0},
        ]
        res = CashFlowForecaster.forecast_liquidity(history, current_balance=10000.0, forecast_days=30)
        self.assertGreater(res.projected_ending_balance, 10000.0)
        self.assertEqual(res.liquidity_status, LiquidityStatus.OPTIMAL)
        self.assertGreater(res.estimated_vat_liability, 0.0)

    def test_forecast_deficit_risk(self):
        history = [
            {"debit_amount": 5000.0, "credit_amount": 100.0},
            {"debit_amount": 5000.0, "credit_amount": 100.0},
        ]
        res = CashFlowForecaster.forecast_liquidity(history, current_balance=1000.0, forecast_days=30)
        self.assertLess(res.projected_ending_balance, 0.0)
        self.assertEqual(res.liquidity_status, LiquidityStatus.DEFICIT_RISK)


if __name__ == "__main__":
    unittest.main()
