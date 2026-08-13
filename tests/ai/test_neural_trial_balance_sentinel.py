"""
Unit tests for Real-Time Accounting Anomaly & Discrepancy Prevention Neural Sentinel (Neural Trial Balance Sentinel).
"""

import json
import unittest

from src.ai.neural_trial_balance_sentinel import (
    AnomalyType,
    NeuralTrialBalanceSentinel,
    SentinelRiskLevel,
    TrialBalanceAccountItem,
)


class TestNeuralTrialBalanceSentinel(unittest.TestCase):
    """Test suite for NeuralTrialBalanceSentinel."""

    def test_evaluate_balanced_trial_balance_no_anomalies(self):
        bank = TrialBalanceAccountItem("503", "Разплащателна сметка", 1000.0, 0.0, 500.0, 200.0, 1300.0, 0.0)
        supplier = TrialBalanceAccountItem("401", "Доставчици", 0.0, 1000.0, 200.0, 500.0, 0.0, 1300.0)

        report = NeuralTrialBalanceSentinel.evaluate_trial_balance([bank, supplier])

        self.assertTrue(report.is_balanced)
        self.assertEqual(report.total_debit_mismatch_eur, 0.0)
        self.assertEqual(len(report.anomalous_accounts), 0)
        self.assertEqual(report.risk_score, 0.0)
        self.assertEqual(report.risk_level, SentinelRiskLevel.SAFE)
        self.assertTrue(report.vat_reconciled)
        self.assertTrue(report.nominal_accounts_closed)

    def test_evaluate_imbalanced_trial_balance_and_active_account_credit_side(self):
        # Asset account with Credit closing balance (Anomaly)
        bank_corrupt = TrialBalanceAccountItem("503", "Разплащателна сметка", 0.0, 0.0, 100.0, 600.0, 0.0, 500.0)
        supplier = TrialBalanceAccountItem("401", "Доставчици", 0.0, 0.0, 0.0, 100.0, 0.0, 100.0)

        report = NeuralTrialBalanceSentinel.evaluate_trial_balance([bank_corrupt, supplier])

        self.assertFalse(report.is_balanced)
        self.assertEqual(report.total_debit_mismatch_eur, 600.0)  # |100 - 700| = 600
        self.assertGreaterEqual(len(report.anomalous_accounts), 1)
        self.assertEqual(report.anomalous_accounts[0]["account_code"], "503")
        self.assertEqual(report.anomalous_accounts[0]["type"], AnomalyType.UNEXPECTED_CREDIT_BALANCE.value)
        self.assertGreater(report.risk_score, 0.4)
        self.assertIn(report.risk_level, [SentinelRiskLevel.MEDIUM_RISK, SentinelRiskLevel.HIGH_RISK, SentinelRiskLevel.CRITICAL_RISK])

    def test_unexpected_debit_balance_passive_account(self):
        # Passive account (Account 401 Suppliers) with closing Debit balance
        supplier_err = TrialBalanceAccountItem("401", "Доставчици", 0.0, 0.0, 500.0, 200.0, 300.0, 0.0)
        bank = TrialBalanceAccountItem("503", "Разплащателна сметка", 0.0, 0.0, 200.0, 500.0, 0.0, 300.0)

        report = NeuralTrialBalanceSentinel.evaluate_trial_balance([supplier_err, bank])

        self.assertTrue(report.is_balanced)  # 500 vs 500
        self.assertEqual(len(report.anomalous_accounts), 2)  # unexpected debit balance 401 & unexpected credit balance 503
        self.assertEqual(report.anomalous_accounts[0]["type"], AnomalyType.UNEXPECTED_DEBIT_BALANCE.value)
        self.assertIn("Дт 503 / Кт 401", report.anomalous_accounts[0]["recommended_entry"])

    def test_mathematical_flow_discrepancy(self):
        # Account 304 Goods with Opening 1000, Period Dr 500, Cr 200 -> Expected Net 1300, actual closing Dr 9999
        goods_err = TrialBalanceAccountItem("304", "Стоки", 1000.0, 0.0, 500.0, 200.0, 9999.0, 0.0)
        capital = TrialBalanceAccountItem("101", "Основен капитал", 0.0, 1000.0, 200.0, 500.0, 0.0, 1300.0)

        report = NeuralTrialBalanceSentinel.evaluate_trial_balance([goods_err, capital])

        math_anomalies = [a for a in report.anomalous_accounts if a["type"] == AnomalyType.MATHEMATICAL_DISCREPANCY.value]
        self.assertGreaterEqual(len(math_anomalies), 1)
        self.assertEqual(math_anomalies[0]["account_code"], "304")

    def test_unclosed_nominal_accounts_at_month_end(self):
        expense = TrialBalanceAccountItem("601", "Разходи за материали", 0.0, 0.0, 1000.0, 0.0, 1000.0, 0.0)
        revenue = TrialBalanceAccountItem("702", "Приходи от продажби", 0.0, 0.0, 0.0, 1000.0, 0.0, 1000.0)

        report = NeuralTrialBalanceSentinel.evaluate_trial_balance([expense, revenue], is_month_end=True)

        self.assertFalse(report.nominal_accounts_closed)
        unclosed = [a for a in report.anomalous_accounts if a["type"] == AnomalyType.UNCLOSED_NOMINAL_ACCOUNT.value]
        self.assertEqual(len(unclosed), 2)
        self.assertIn("Дт 123 / Кт 601", unclosed[0]["recommended_entry"])
        self.assertIn("Дт 702 / Кт 123", unclosed[1]["recommended_entry"])

    def test_vat_settlement_reconciliation_mismatch(self):
        vat_purchases = TrialBalanceAccountItem("4531", "Наличен ДДС", 0.0, 0.0, 200.0, 0.0, 200.0, 0.0)
        vat_sales = TrialBalanceAccountItem("4532", "Начислен ДДС", 0.0, 0.0, 0.0, 200.0, 0.0, 200.0)

        report = NeuralTrialBalanceSentinel.evaluate_trial_balance([vat_purchases, vat_sales], is_month_end=True)

        self.assertFalse(report.vat_reconciled)
        vat_anomalies = [a for a in report.anomalous_accounts if a["type"] == AnomalyType.VAT_SETTLEMENT_MISMATCH.value]
        self.assertEqual(len(vat_anomalies), 1)
        self.assertIn("Дт 4532 / Кт 4531", vat_anomalies[0]["recommended_entry"])

    def test_predict_anomaly_probabilities(self):
        bank = TrialBalanceAccountItem("503", "Разплащателна сметка", 1000.0, 0.0, 500.0, 200.0, 1300.0, 0.0)
        supplier = TrialBalanceAccountItem("401", "Доставчици", 0.0, 1000.0, 200.0, 500.0, 0.0, 1300.0)

        probs = NeuralTrialBalanceSentinel.predict_anomaly_probabilities([bank, supplier])

        self.assertIn("debit_credit_imbalance", probs)
        self.assertIn("unexpected_side_balance", probs)
        self.assertEqual(probs["debit_credit_imbalance"], 0.02)

    def test_format_sentinel_report_json(self):
        bank = TrialBalanceAccountItem("503", "Разплащателна сметка", 1000.0, 0.0, 500.0, 200.0, 1300.0, 0.0)
        supplier = TrialBalanceAccountItem("401", "Доставчици", 0.0, 1000.0, 200.0, 500.0, 0.0, 1300.0)

        report = NeuralTrialBalanceSentinel.evaluate_trial_balance([bank, supplier])
        json_str = NeuralTrialBalanceSentinel.format_sentinel_report_json(report)

        parsed = json.loads(json_str)
        self.assertTrue(parsed["is_balanced"])
        self.assertEqual(parsed["risk_level"], "SAFE")


if __name__ == "__main__":
    unittest.main()
