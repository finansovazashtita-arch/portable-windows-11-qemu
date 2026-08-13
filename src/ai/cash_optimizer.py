"""
Autonomous Dynamic Cash Flow Optimization & Predictive Liquidity AI Engine.

Milestone M64: m64_ai_cash_optimizer
Expands liquidity forecasting with:
1. Monte Carlo simulations for stochastic liquidity risk modeling (VaR 95/99%, deficit probabilities, percentiles).
2. Automated supplier payment scheduler maximizing net cash discount yield vs cost of capital & interest rates.
3. Bulgarian double-entry journal recommendations (Account 401 -> 503 / 709).
"""

import dataclasses
import datetime
import enum
import hashlib
import json
import logging
import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("cash_optimizer")


class OptimizationStrategy(str, enum.Enum):
    AGGRESSIVE_DISCOUNT = "AGGRESSIVE_DISCOUNT"
    BALANCED_LIQUIDITY = "BALANCED_LIQUIDITY"
    CONSERVATIVE_PRESERVATION = "CONSERVATIVE_PRESERVATION"


@dataclasses.dataclass
class SupplierInvoice:
    """Dataclass representing a pending vendor/supplier invoice."""

    invoice_id: str
    vendor_eik: str
    vendor_name: str
    amount_bgn: float
    invoice_date: str  # YYYY-MM-DD
    due_date: str  # YYYY-MM-DD
    cash_discount_percent: float = 0.0  # e.g. 2.0 for 2% discount
    cash_discount_days: int = 0  # Days from invoice_date to qualify for discount
    late_payment_penalty_rate_annual: float = 10.0  # 10% annual penalty rate
    priority: int = 1  # 1 = highest, 5 = lowest
    account_code: str = "401"
    iban: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class MonteCarloSimulationResult:
    """Dataclass holding Monte Carlo liquidity projection metrics."""

    iterations: int
    forecast_days: int
    starting_balance: float
    percentile_5: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_95: float
    expected_ending_balance: float
    var_95: float  # Value at Risk at 95% confidence
    var_99: float  # Value at Risk at 99% confidence
    probability_of_deficit: float  # P(Balance < 0)
    probability_below_safety_buffer: float  # P(Balance < safety_buffer)
    recommended_safety_buffer: float
    daily_trajectory_median: List[float]
    daily_trajectory_p5: List[float]
    daily_trajectory_p95: List[float]

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class PaymentScheduleItem:
    """Dataclass holding scheduled payment decision for a single supplier invoice."""

    invoice_id: str
    vendor_name: str
    amount_bgn: float
    scheduled_payment_date: str  # YYYY-MM-DD
    original_due_date: str  # YYYY-MM-DD
    discount_applied: bool
    discount_amount_bgn: float
    net_payment_amount_bgn: float
    penalty_incurred_bgn: float
    opportunity_cost_bgn: float
    net_financial_benefit_bgn: float
    annualized_return_on_capital_pct: float
    debit_account: str = "401"
    credit_account: str = "503"
    discount_account: str = "709"
    journal_entry_recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class OptimizedPaymentSchedule:
    """Dataclass holding aggregated payment schedule and ROI metrics."""

    strategy: OptimizationStrategy
    total_invoices_processed: int
    total_gross_payable_bgn: float
    total_scheduled_payout_bgn: float
    total_discounts_captured_bgn: float
    total_penalties_avoided_bgn: float
    total_net_financial_benefit_bgn: float
    overall_roi_pct: float
    safety_buffer_maintained_bgn: float
    minimum_projected_cash_bgn: float
    schedule_items: List[PaymentScheduleItem]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        res = dataclasses.asdict(self)
        res["strategy"] = self.strategy.value
        return res


@dataclasses.dataclass
class CashOptimizationResult:
    """Master output structure for cash flow optimization & predictive liquidity engine."""

    current_cash_balance: float
    annual_cost_of_capital_rate: float
    monte_carlo_simulation: MonteCarloSimulationResult
    optimized_schedule: OptimizedPaymentSchedule
    vat_tax_reserve_bgn: float
    recommended_action: str
    audit_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_cash_balance": self.current_cash_balance,
            "annual_cost_of_capital_rate": self.annual_cost_of_capital_rate,
            "monte_carlo_simulation": self.monte_carlo_simulation.to_dict(),
            "optimized_schedule": self.optimized_schedule.to_dict(),
            "vat_tax_reserve_bgn": self.vat_tax_reserve_bgn,
            "recommended_action": self.recommended_action,
            "audit_hash": self.audit_hash,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class AICashOptimizer:
    """Autonomous Dynamic Cash Flow Optimization & Predictive Liquidity AI Engine."""

    @classmethod
    def run_monte_carlo_simulation(
        cls,
        starting_balance: float = 50000.0,
        forecast_days: int = 30,
        iterations: int = 1000,
        daily_inflow_mean: float = 3000.0,
        daily_inflow_std: float = 800.0,
        daily_outflow_mean: float = 2500.0,
        daily_outflow_std: float = 600.0,
        receivables_delay_prob: float = 0.15,
        receivables_delay_days: int = 5,
        tax_reserve_days: List[int] = None,
        vat_liability_estimate: float = 4000.0,
        random_seed: Optional[int] = 42,
    ) -> MonteCarloSimulationResult:
        """Executes Monte Carlo stochastic simulation over target days horizon."""
        if random_seed is not None:
            random.seed(random_seed)

        if tax_reserve_days is None:
            tax_reserve_days = [14]  # Bulgarian 14th day monthly VAT payment deadline

        simulation_paths: List[List[float]] = []
        ending_balances: List[float] = []
        deficit_counts = 0
        below_buffer_counts = 0

        # Heuristic safety buffer (15 days of mean daily outflows)
        recommended_buffer = round(daily_outflow_mean * 15.0, 2)

        for _ in range(iterations):
            current_path = [starting_balance]
            balance = starting_balance
            has_deficit = False
            has_below_buffer = False

            for day in range(1, forecast_days + 1):
                # Sample daily inflow & outflow from normal distribution
                inflow = max(0.0, random.gauss(daily_inflow_mean, daily_inflow_std))
                outflow = max(0.0, random.gauss(daily_outflow_mean, daily_outflow_std))

                # Receivables delay shock
                if random.random() < receivables_delay_prob:
                    inflow *= 0.3  # 70% reduction on delayed payment days

                # Scheduled VAT Tax payment shock
                if day in tax_reserve_days:
                    outflow += vat_liability_estimate

                balance += inflow - outflow
                current_path.append(balance)

                if balance < 0:
                    has_deficit = True
                if balance < recommended_buffer:
                    has_below_buffer = True

            simulation_paths.append(current_path)
            ending_balances.append(balance)
            if has_deficit:
                deficit_counts += 1
            if has_below_buffer:
                below_buffer_counts += 1

        ending_balances.sort()

        def percentile(arr: List[float], p: float) -> float:
            idx = int(p * (len(arr) - 1))
            return arr[idx]

        p5 = round(percentile(ending_balances, 0.05), 2)
        p25 = round(percentile(ending_balances, 0.25), 2)
        p50 = round(percentile(ending_balances, 0.50), 2)
        p75 = round(percentile(ending_balances, 0.75), 2)
        p95 = round(percentile(ending_balances, 0.95), 2)
        expected_ending = round(sum(ending_balances) / len(ending_balances), 2)

        # Value at Risk (VaR) relative to starting balance or mean
        var_95 = round(max(0.0, starting_balance - p5), 2)
        var_99 = round(max(0.0, starting_balance - percentile(ending_balances, 0.01)), 2)

        prob_deficit = round(deficit_counts / iterations, 4)
        prob_below_buffer = round(below_buffer_counts / iterations, 4)

        # Compute median, p5, and p95 daily trajectories across days
        daily_median: List[float] = []
        daily_p5: List[float] = []
        daily_p95: List[float] = []

        for d in range(forecast_days + 1):
            day_values = sorted([path[d] for path in simulation_paths])
            daily_p5.append(round(percentile(day_values, 0.05), 2))
            daily_median.append(round(percentile(day_values, 0.50), 2))
            daily_p95.append(round(percentile(day_values, 0.95), 2))

        logger.info(
            f"🎲 Monte Carlo Simulation ({iterations} iter, {forecast_days} days): "
            f"Expected €/BGN {expected_ending:,.2f} | VaR 95%: {var_95:,.2f} | Deficit Prob: {prob_deficit*100:.1f}%"
        )

        return MonteCarloSimulationResult(
            iterations=iterations,
            forecast_days=forecast_days,
            starting_balance=round(starting_balance, 2),
            percentile_5=p5,
            percentile_25=p25,
            percentile_50=p50,
            percentile_75=p75,
            percentile_95=p95,
            expected_ending_balance=expected_ending,
            var_95=var_95,
            var_99=var_99,
            probability_of_deficit=prob_deficit,
            probability_below_safety_buffer=prob_below_buffer,
            recommended_safety_buffer=recommended_buffer,
            daily_trajectory_median=daily_median,
            daily_trajectory_p5=daily_p5,
            daily_trajectory_p95=daily_p95,
        )

    @classmethod
    def optimize_payment_schedule(
        cls,
        invoices: List[SupplierInvoice],
        current_cash_balance: float = 50000.0,
        annual_cost_of_capital_rate: float = 0.06,  # 6% per annum cost of short-term credit line
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED_LIQUIDITY,
        safety_buffer: float = 15000.0,
        start_date_str: str = "2026-06-01",
    ) -> OptimizedPaymentSchedule:
        """Schedules supplier invoice payments to maximize cash discount yield & avoid penalties while respecting liquidity safety buffer."""
        if not invoices:
            return OptimizedPaymentSchedule(
                strategy=strategy,
                total_invoices_processed=0,
                total_gross_payable_bgn=0.0,
                total_scheduled_payout_bgn=0.0,
                total_discounts_captured_bgn=0.0,
                total_penalties_avoided_bgn=0.0,
                total_net_financial_benefit_bgn=0.0,
                overall_roi_pct=0.0,
                safety_buffer_maintained_bgn=safety_buffer,
                minimum_projected_cash_bgn=current_cash_balance,
                schedule_items=[],
                recommendations=["Няма предоставени фактури за оптимизация."],
            )

        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()

        # Parse invoice dates and compute financial yield for early payment
        scored_items: List[Dict[str, Any]] = []
        for inv in invoices:
            inv_date = datetime.datetime.strptime(inv.invoice_date, "%Y-%m-%d").date()
            due_date = datetime.datetime.strptime(inv.due_date, "%Y-%m-%d").date()

            if inv.cash_discount_days > 0 and inv.cash_discount_percent > 0:
                discount_deadline = inv_date + datetime.timedelta(days=inv.cash_discount_days)
            else:
                discount_deadline = due_date

            days_saved = max((due_date - discount_deadline).days, 1)

            # Cash discount amount
            discount_amount = round(inv.amount_bgn * (inv.cash_discount_percent / 100.0), 2)
            net_payment = round(inv.amount_bgn - discount_amount, 2)

            # Opportunity cost of paying early (interest lost/incurred over days_saved)
            daily_capital_rate = annual_cost_of_capital_rate / 365.0
            opportunity_cost = round(net_payment * daily_capital_rate * days_saved, 2)

            # Net financial benefit
            net_benefit = round(discount_amount - opportunity_cost, 2)

            # Annualized Effective Return on Capital
            if net_payment > 0 and days_saved > 0:
                discount_fraction = inv.cash_discount_percent / (100.0 - inv.cash_discount_percent)
                annualized_return = round(discount_fraction * (365.0 / days_saved) * 100.0, 2)
            else:
                annualized_return = 0.0

            scored_items.append(
                {
                    "invoice": inv,
                    "inv_date": inv_date,
                    "due_date": due_date,
                    "discount_deadline": discount_deadline,
                    "days_saved": days_saved,
                    "discount_amount": discount_amount,
                    "net_payment": net_payment,
                    "opportunity_cost": opportunity_cost,
                    "net_benefit": net_benefit,
                    "annualized_return": annualized_return,
                }
            )

        # Sort items according to Strategy
        if strategy == OptimizationStrategy.AGGRESSIVE_DISCOUNT:
            # Rank purely by Net Financial Benefit / Annualized Return
            scored_items.sort(key=lambda x: (-x["net_benefit"], -x["annualized_return"], x["due_date"]))
        elif strategy == OptimizationStrategy.CONSERVATIVE_PRESERVATION:
            # Pay on due date to conserve cash as long as possible
            scored_items.sort(key=lambda x: (x["due_date"], x["invoice"].priority))
        else:  # BALANCED_LIQUIDITY
            # Balanced: rank high ROI discounts first, then by due date
            scored_items.sort(key=lambda x: (-x["net_benefit"], x["due_date"], x["invoice"].priority))

        running_cash = current_cash_balance
        min_cash_observed = current_cash_balance
        schedule_items: List[PaymentScheduleItem] = []

        total_gross = sum(inv.amount_bgn for inv in invoices)
        total_payout = 0.0
        total_discounts = 0.0
        total_penalties_avoided = 0.0
        total_net_benefit = 0.0

        for item in scored_items:
            inv: SupplierInvoice = item["invoice"]
            due_date = item["due_date"]
            discount_deadline = item["discount_deadline"]
            net_pay = item["net_payment"]
            disc_amt = item["discount_amount"]
            net_ben = item["net_benefit"]
            ann_ret = item["annualized_return"]

            can_take_discount = False
            scheduled_date = due_date

            if strategy in [OptimizationStrategy.AGGRESSIVE_DISCOUNT, OptimizationStrategy.BALANCED_LIQUIDITY]:
                if disc_amt > 0 and net_ben > 0 and discount_deadline >= start_date:
                    # Check if paying at discount deadline respects safety buffer
                    if (running_cash - net_pay) >= safety_buffer:
                        can_take_discount = True
                        scheduled_date = max(start_date, discount_deadline)

            if not can_take_discount:
                # Pay on due date (or start_date if overdue)
                scheduled_date = max(start_date, due_date)
                actual_pay_amount = inv.amount_bgn
                actual_discount = 0.0
                actual_opportunity_cost = 0.0
                actual_penalty = 0.0

                # If overdue, calculate penalty
                if scheduled_date > due_date:
                    overdue_days = (scheduled_date - due_date).days
                    daily_penalty_rate = (inv.late_payment_penalty_rate_annual / 100.0) / 365.0
                    actual_penalty = round(inv.amount_bgn * daily_penalty_rate * overdue_days, 2)
                    actual_pay_amount += actual_penalty

                actual_net_benefit = -actual_penalty
                ann_ret = 0.0
            else:
                actual_pay_amount = net_pay
                actual_discount = disc_amt
                actual_opportunity_cost = item["opportunity_cost"]
                actual_penalty = 0.0
                actual_net_benefit = net_ben

            running_cash -= actual_pay_amount
            if running_cash < min_cash_observed:
                min_cash_observed = running_cash

            total_payout += actual_pay_amount
            total_discounts += actual_discount
            total_net_benefit += actual_net_benefit

            # Estimated penalty avoided by paying before/on due date
            potential_overdue_days = max(15, (due_date - start_date).days)
            pen_avoided = round(inv.amount_bgn * ((inv.late_payment_penalty_rate_annual / 100.0) / 365.0) * potential_overdue_days, 2)
            total_penalties_avoided += pen_avoided

            # Double entry accounting representation
            if actual_discount > 0:
                j_entry = (
                    f"Дт {inv.account_code} (Доставчик {inv.vendor_name}): BGN {inv.amount_bgn:,.2f} | "
                    f"Кт 503 (Разплащателна сметка): BGN {actual_pay_amount:,.2f} | "
                    f"Кт 709 (Приходи от касови отстъпки): BGN {actual_discount:,.2f}"
                )
            else:
                j_entry = (
                    f"Дт {inv.account_code} (Доставчик {inv.vendor_name}): BGN {inv.amount_bgn:,.2f} | "
                    f"Кт 503 (Разплащателна сметка): BGN {actual_pay_amount:,.2f}"
                )

            schedule_items.append(
                PaymentScheduleItem(
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    amount_bgn=inv.amount_bgn,
                    scheduled_payment_date=scheduled_date.strftime("%Y-%m-%d"),
                    original_due_date=due_date.strftime("%Y-%m-%d"),
                    discount_applied=can_take_discount,
                    discount_amount_bgn=actual_discount,
                    net_payment_amount_bgn=actual_pay_amount,
                    penalty_incurred_bgn=actual_penalty,
                    opportunity_cost_bgn=actual_opportunity_cost,
                    net_financial_benefit_bgn=actual_net_benefit,
                    annualized_return_on_capital_pct=ann_ret,
                    debit_account=inv.account_code,
                    credit_account="503",
                    discount_account="709",
                    journal_entry_recommendation=j_entry,
                )
            )

        overall_roi = round((total_discounts / total_gross * 100.0), 2) if total_gross > 0 else 0.0

        recommendations = [
            f"💡 Приложена стратегия: {strategy.value}",
            f"💶 Общо спестени касови отстъпки: BGN {total_discounts:,.2f} (ROI: {overall_roi:.2f}%)",
            f"📈 Чист финансов ефект (нето полза): BGN {total_net_benefit:,.2f}",
            f"🛡️ Поддържан ликвиден буфер: BGN {safety_buffer:,.2f} (Минимално наблюдаван баланс: BGN {min_cash_observed:,.2f})",
        ]

        if min_cash_observed < safety_buffer:
            recommendations.append("⚠️ ВНИМАНИЕ: Наличността спада под ликвидния буфер в определени дни от графика.")

        logger.info(
            f"📊 Payment Schedule Optimized ({len(schedule_items)} invoices): "
            f"Discounts BGN {total_discounts:,.2f} | Payout BGN {total_payout:,.2f}"
        )

        return OptimizedPaymentSchedule(
            strategy=strategy,
            total_invoices_processed=len(schedule_items),
            total_gross_payable_bgn=round(total_gross, 2),
            total_scheduled_payout_bgn=round(total_payout, 2),
            total_discounts_captured_bgn=round(total_discounts, 2),
            total_penalties_avoided_bgn=round(total_penalties_avoided, 2),
            total_net_financial_benefit_bgn=round(total_net_benefit, 2),
            overall_roi_pct=overall_roi,
            safety_buffer_maintained_bgn=round(safety_buffer, 2),
            minimum_projected_cash_bgn=round(min_cash_observed, 2),
            schedule_items=schedule_items,
            recommendations=recommendations,
        )

    @classmethod
    def run_full_cash_optimization(
        cls,
        invoices: List[SupplierInvoice],
        current_cash_balance: float = 50000.0,
        annual_cost_of_capital_rate: float = 0.06,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED_LIQUIDITY,
        forecast_days: int = 30,
        iterations: int = 1000,
        daily_inflow_mean: float = 3000.0,
        daily_inflow_std: float = 800.0,
        daily_outflow_mean: float = 2500.0,
        daily_outflow_std: float = 600.0,
        vat_liability_estimate: float = 4000.0,
        random_seed: Optional[int] = 42,
    ) -> CashOptimizationResult:
        """Runs integrated Monte Carlo risk simulation and supplier payment schedule optimization."""

        # 1. Run Monte Carlo simulation
        mc_result = cls.run_monte_carlo_simulation(
            starting_balance=current_cash_balance,
            forecast_days=forecast_days,
            iterations=iterations,
            daily_inflow_mean=daily_inflow_mean,
            daily_inflow_std=daily_inflow_std,
            daily_outflow_mean=daily_outflow_mean,
            daily_outflow_std=daily_outflow_std,
            vat_liability_estimate=vat_liability_estimate,
            random_seed=random_seed,
        )

        # 2. Dynamic safety buffer from Monte Carlo or explicit minimum
        effective_safety_buffer = max(mc_result.recommended_safety_buffer, 10000.0)

        # 3. Optimize supplier payment schedule
        opt_schedule = cls.optimize_payment_schedule(
            invoices=invoices,
            current_cash_balance=current_cash_balance,
            annual_cost_of_capital_rate=annual_cost_of_capital_rate,
            strategy=strategy,
            safety_buffer=effective_safety_buffer,
        )

        # 4. Formulate executive action recommendation
        if mc_result.probability_of_deficit > 0.05:
            rec_action = (
                f"🚨 ВИСОК ЛИКВИДЕН РИСК: Вероятност за дефицит {mc_result.probability_of_deficit*100:.1f}%. "
                f"Препоръчва се преминаване към CONSERVATIVE_PRESERVATION стратегия и осигуряване на кредитна линия."
            )
        elif opt_schedule.total_discounts_captured_bgn > 0:
            rec_action = (
                f"✅ ОПТИМАЛНО УПРАВЛЕНИЕ НА КАСОВИТЕ ПОТОЦИ: Спестени BGN {opt_schedule.total_discounts_captured_bgn:,.2f} "
                f"от касови отстъпки при поддържан ликвиден буфер BGN {effective_safety_buffer:,.2f}."
            )
        else:
            rec_action = "ℹ️ СТАБИЛНА ЛИКВИДНОСТ: Плащанията са планирани на падеж без дефицитен риск."

        # 5. Generate cryptographic SHA-256 hash for audit trail integrity
        hash_payload = (
            f"{current_cash_balance}|{annual_cost_of_capital_rate}|{strategy.value}|"
            f"{mc_result.expected_ending_balance}|{opt_schedule.total_discounts_captured_bgn}|{len(invoices)}"
        )
        audit_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        logger.info(f"✨ Full Cash Optimization Completed | SHA-256 Audit: {audit_hash[:16]}...")

        return CashOptimizationResult(
            current_cash_balance=round(current_cash_balance, 2),
            annual_cost_of_capital_rate=annual_cost_of_capital_rate,
            monte_carlo_simulation=mc_result,
            optimized_schedule=opt_schedule,
            vat_tax_reserve_bgn=round(vat_liability_estimate, 2),
            recommended_action=rec_action,
            audit_hash=audit_hash,
        )
