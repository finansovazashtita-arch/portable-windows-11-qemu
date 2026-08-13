"""
Unit tests for Autonomous Dynamic Cash Flow Optimization & Predictive Liquidity AI Engine.
"""

import json
import unittest

from src.ai.cash_optimizer import (
    AICashOptimizer,
    CashOptimizationResult,
    MonteCarloSimulationResult,
    OptimizationStrategy,
    OptimizedPaymentSchedule,
    PaymentScheduleItem,
    SupplierInvoice,
)


class TestAICashOptimizer(unittest.TestCase):
    """Test suite for AICashOptimizer module (M64)."""

    def setUp(self):
        self.sample_invoices = [
            SupplierInvoice(
                invoice_id="INV-2026-001",
                vendor_eik="123456789",
                vendor_name="ТехноСнаб ООД",
                amount_bgn=10000.0,
                invoice_date="2026-06-01",
                due_date="2026-06-30",
                cash_discount_percent=3.0,  # 3% discount
                cash_discount_days=10,  # Discount deadline: 2026-06-11
                late_payment_penalty_rate_annual=10.0,
                priority=1,
            ),
            SupplierInvoice(
                invoice_id="INV-2026-002",
                vendor_eik="987654321",
                vendor_name="ЕнергоПро АД",
                amount_bgn=5000.0,
                invoice_date="2026-06-01",
                due_date="2026-06-15",
                cash_discount_percent=1.0,  # 1% discount
                cash_discount_days=5,  # Discount deadline: 2026-06-06
                late_payment_penalty_rate_annual=12.0,
                priority=2,
            ),
            SupplierInvoice(
                invoice_id="INV-2026-003",
                vendor_eik="555666777",
                vendor_name="БулТранс ЕООД",
                amount_bgn=12000.0,
                invoice_date="2026-06-01",
                due_date="2026-06-25",
                cash_discount_percent=0.0,  # No discount
                cash_discount_days=0,
                late_payment_penalty_rate_annual=8.0,
                priority=3,
            ),
        ]

    def test_monte_carlo_simulation_metrics(self):
        result = AICashOptimizer.run_monte_carlo_simulation(
            starting_balance=60000.0,
            forecast_days=30,
            iterations=500,
            daily_inflow_mean=4000.0,
            daily_outflow_mean=3000.0,
            random_seed=123,
        )

        self.assertIsInstance(result, MonteCarloSimulationResult)
        self.assertEqual(result.iterations, 500)
        self.assertEqual(result.forecast_days, 30)
        self.assertLessEqual(result.percentile_5, result.percentile_25)
        self.assertLessEqual(result.percentile_25, result.percentile_50)
        self.assertLessEqual(result.percentile_50, result.percentile_75)
        self.assertLessEqual(result.percentile_75, result.percentile_95)
        self.assertGreaterEqual(result.var_95, 0.0)
        self.assertGreaterEqual(result.recommended_safety_buffer, 10000.0)
        self.assertEqual(len(result.daily_trajectory_median), 31)

    def test_supplier_invoice_discount_optimization(self):
        schedule = AICashOptimizer.optimize_payment_schedule(
            invoices=self.sample_invoices,
            current_cash_balance=80000.0,
            annual_cost_of_capital_rate=0.05,
            strategy=OptimizationStrategy.AGGRESSIVE_DISCOUNT,
            safety_buffer=10000.0,
            start_date_str="2026-06-01",
        )

        self.assertIsInstance(schedule, OptimizedPaymentSchedule)
        self.assertEqual(schedule.total_invoices_processed, 3)
        self.assertGreater(schedule.total_discounts_captured_bgn, 0.0)
        # Check discount capture for INV-2026-001 (3% of 10000 = 300 BGN)
        inv1_item = next(item for item in schedule.schedule_items if item.invoice_id == "INV-2026-001")
        self.assertTrue(inv1_item.discount_applied)
        self.assertEqual(inv1_item.discount_amount_bgn, 300.0)
        self.assertEqual(inv1_item.net_payment_amount_bgn, 9700.0)
        self.assertEqual(inv1_item.scheduled_payment_date, "2026-06-11")
        self.assertIn("Кт 709", inv1_item.journal_entry_recommendation)

    def test_conservative_strategy_preserves_cash(self):
        schedule = AICashOptimizer.optimize_payment_schedule(
            invoices=self.sample_invoices,
            current_cash_balance=80000.0,
            annual_cost_of_capital_rate=0.05,
            strategy=OptimizationStrategy.CONSERVATIVE_PRESERVATION,
            safety_buffer=10000.0,
            start_date_str="2026-06-01",
        )

        # Under conservative strategy, payments are scheduled on original due dates
        inv1_item = next(item for item in schedule.schedule_items if item.invoice_id == "INV-2026-001")
        self.assertFalse(inv1_item.discount_applied)
        self.assertEqual(inv1_item.scheduled_payment_date, "2026-06-30")

    def test_safety_buffer_constraint_prevents_risky_discounts(self):
        # Setting cash balance where total invoices (27,000) fit base payout (ending cash 8,000 >= 0),
        # but early discount payment (9,700) would breach safety buffer (28,000).
        schedule = AICashOptimizer.optimize_payment_schedule(
            invoices=self.sample_invoices,
            current_cash_balance=35000.0,
            annual_cost_of_capital_rate=0.05,
            strategy=OptimizationStrategy.BALANCED_LIQUIDITY,
            safety_buffer=28000.0,  # Buffer leaves only 7,000 BGN available above buffer
            start_date_str="2026-06-01",
        )

        # INV-2026-001 net payment is 9,700, which exceeds available cash above buffer (7,000)
        inv1_item = next(item for item in schedule.schedule_items if item.invoice_id == "INV-2026-001")
        self.assertFalse(inv1_item.discount_applied)
        self.assertGreaterEqual(schedule.minimum_projected_cash_bgn, 0.0)

    def test_run_full_cash_optimization_e2e(self):
        res = AICashOptimizer.run_full_cash_optimization(
            invoices=self.sample_invoices,
            current_cash_balance=70000.0,
            annual_cost_of_capital_rate=0.06,
            strategy=OptimizationStrategy.BALANCED_LIQUIDITY,
            forecast_days=30,
            iterations=200,
            random_seed=42,
        )

        self.assertIsInstance(res, CashOptimizationResult)
        self.assertEqual(res.current_cash_balance, 70000.0)
        self.assertGreater(len(res.audit_hash), 30)
        self.assertIn("ОПТИМАЛНО", res.recommended_action)

        # JSON serialization test
        json_str = res.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["current_cash_balance"], 70000.0)
        self.assertIn("monte_carlo_simulation", parsed)
        self.assertIn("optimized_schedule", parsed)

    def test_empty_invoices_graceful_handling(self):
        schedule = AICashOptimizer.optimize_payment_schedule(
            invoices=[],
            current_cash_balance=50000.0,
        )
        self.assertEqual(schedule.total_invoices_processed, 0)
        self.assertEqual(schedule.total_discounts_captured_bgn, 0.0)
        self.assertIn("Няма предоставени", schedule.recommendations[0])


if __name__ == "__main__":
    unittest.main()
