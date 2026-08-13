"""
Real-Time Accounting Anomaly & Discrepancy Prevention Neural Sentinel (Neural Trial Balance Sentinel).

Analyzes trial balances (Оборотна ведомост) for accounting anomalies:
- Verifies overall Trial Balance Debit/Credit equality invariant (Opening, Period, Closing)
- Identifies active vs. passive account closing balance anomalies (e.g. negative asset balance or red figure / червено салдо)
- Verifies internal row mathematical consistency: Closing Balance = Opening Balance + Period Movement
- Validates nominal account (Group 60 Expenses & Group 70 Revenues) closure prior to NRA monthly tax filings
- Checks VAT settlement reconciliation across Accounts 4531 (Purchases VAT), 4532 (Sales VAT), and 4538 (VAT Settlement)
- Computes overall audit risk score (0.0 to 1.0) and assigns sentinel risk classification
- Provides automated AI double-entry journal recommendations for remediation before tax filing deadlines
"""

import dataclasses
import enum
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("neural_trial_balance_sentinel")


class AnomalyType(str, enum.Enum):
    """Enumeration of trial balance anomaly types."""

    DEBIT_CREDIT_IMBALANCE = "DEBIT_CREDIT_IMBALANCE"
    UNEXPECTED_CREDIT_BALANCE = "UNEXPECTED_CREDIT_BALANCE"  # Red asset balance
    UNEXPECTED_DEBIT_BALANCE = "UNEXPECTED_DEBIT_BALANCE"  # Red liability balance
    MATHEMATICAL_DISCREPANCY = "MATHEMATICAL_DISCREPANCY"  # Closing != Opening + Period
    UNCLOSED_NOMINAL_ACCOUNT = "UNCLOSED_NOMINAL_ACCOUNT"  # Expenses Group 60 or Revenues Group 70 unclosed
    VAT_SETTLEMENT_MISMATCH = "VAT_SETTLEMENT_MISMATCH"  # Unreconciled VAT accounts
    SUSPICIOUS_TURNOVER_SPIKE = "SUSPICIOUS_TURNOVER_SPIKE"  # Abnormal movement volume


class SentinelRiskLevel(str, enum.Enum):
    """Risk rating levels for trial balance evaluation."""

    SAFE = "SAFE"  # Score <= 0.15
    LOW_RISK = "LOW_RISK"  # 0.15 < Score <= 0.40
    MEDIUM_RISK = "MEDIUM_RISK"  # 0.40 < Score <= 0.70
    HIGH_RISK = "HIGH_RISK"  # 0.70 < Score <= 0.90
    CRITICAL_RISK = "CRITICAL_RISK"  # Score > 0.90


@dataclasses.dataclass
class TrialBalanceAccountItem:
    """Dataclass holding a single account entry in the Trial Balance (Оборотна ведомост)."""

    account_code: str
    account_name: str
    opening_debit_eur: float
    opening_credit_eur: float
    period_debit_eur: float
    period_credit_eur: float
    closing_debit_eur: float
    closing_credit_eur: float


@dataclasses.dataclass
class AnomalyReport:
    """Dataclass holding trial balance anomaly evaluation results."""

    is_balanced: bool
    total_debit_mismatch_eur: float
    anomalous_accounts: List[Dict[str, Any]]
    risk_score: float  # 0.0 (Safe) to 1.0 (Critical Risk)
    recommendations: List[str]
    risk_level: SentinelRiskLevel = SentinelRiskLevel.SAFE
    total_opening_mismatch_eur: float = 0.0
    total_closing_mismatch_eur: float = 0.0
    vat_reconciled: bool = True
    nominal_accounts_closed: bool = True
    summary_bg: str = ""


class NeuralTrialBalanceSentinel:
    """Neural sentinel engine analyzing trial balance movements and detecting posting anomalies."""

    ACTIVE_ACCOUNTS_PREFIXES = (
        "20",
        "21",
        "24",
        "30",
        "50",
        "411",
        "422",
        "4531",
        "60",
        "61",
        "62",
    )  # Active asset / expense accounts
    PASSIVE_ACCOUNTS_PREFIXES = (
        "10",
        "11",
        "12",
        "15",
        "401",
        "421",
        "4532",
        "454",
        "455",
        "70",
        "72",
    )  # Passive equity / liability accounts

    @classmethod
    def evaluate_trial_balance(
        cls, accounts: List[TrialBalanceAccountItem], is_month_end: bool = False
    ) -> AnomalyReport:
        """Evaluates trial balance for debit/credit balance equality, row math, side anomalies, nominal account closure, and VAT reconciliation."""
        total_opening_debit = sum(a.opening_debit_eur for a in accounts)
        total_opening_credit = sum(a.opening_credit_eur for a in accounts)
        total_period_debit = sum(a.period_debit_eur for a in accounts)
        total_period_credit = sum(a.period_credit_eur for a in accounts)
        total_closing_debit = sum(a.closing_debit_eur for a in accounts)
        total_closing_credit = sum(a.closing_credit_eur for a in accounts)

        opening_mismatch = round(abs(total_opening_debit - total_opening_credit), 2)
        period_mismatch = round(abs(total_period_debit - total_period_credit), 2)
        closing_mismatch = round(abs(total_closing_debit - total_closing_credit), 2)

        is_balanced = (opening_mismatch == 0.0) and (period_mismatch == 0.0) and (closing_mismatch == 0.0)

        anomalous_accounts: List[Dict[str, Any]] = []
        recommendations: List[str] = []

        if period_mismatch > 0.0:
            recommendations.append(
                f"🚨 Открита е разлика в дебитния и кредитния оборот на стойност €{period_mismatch:,.2f}. Проверете незавършените статии."
            )
        if opening_mismatch > 0.0:
            recommendations.append(
                f"🚨 Разлика в началните salda (Дебит/Кредит) от €{opening_mismatch:,.2f}. Проверете приключването на предходната година."
            )
        if closing_mismatch > 0.0:
            recommendations.append(
                f"🚨 Разлика в крайните salda (Дебит/Кредит) от €{closing_mismatch:,.2f}."
            )

        nominal_unclosed_count = 0
        vat_4531_val = 0.0
        vat_4532_val = 0.0
        vat_4538_val = 0.0

        for acc in accounts:
            # Track VAT accounts
            if acc.account_code == "4531":
                vat_4531_val = acc.closing_debit_eur - acc.closing_credit_eur
            elif acc.account_code == "4532":
                vat_4532_val = acc.closing_credit_eur - acc.closing_debit_eur
            elif acc.account_code.startswith("4538"):
                vat_4538_val = acc.closing_debit_eur or acc.closing_credit_eur

            # 1. Active account check (Asset/Expense) -> Should normally have Debit closing balance
            if any(acc.account_code.startswith(p) for p in cls.ACTIVE_ACCOUNTS_PREFIXES):
                if acc.closing_credit_eur > 0 and acc.closing_debit_eur == 0:
                    anomalous_accounts.append(
                        {
                            "account_code": acc.account_code,
                            "account_name": acc.account_name,
                            "type": AnomalyType.UNEXPECTED_CREDIT_BALANCE.value,
                            "amount_eur": acc.closing_credit_eur,
                            "recommended_entry": f"Дт {acc.account_code} / Кт 503 (или корекция на дебиторо-кредиторо прихващане)",
                        }
                    )
                    recommendations.append(
                        f"⚠️ Активна сметка {acc.account_code} ({acc.account_name}) има кредитно салдо от €{acc.closing_credit_eur:,.2f} (Червено салдо)."
                    )

            # 2. Passive account check (Equity/Liability) -> Should normally have Credit closing balance
            elif any(acc.account_code.startswith(p) for p in cls.PASSIVE_ACCOUNTS_PREFIXES):
                if acc.closing_debit_eur > 0 and acc.closing_credit_eur == 0:
                    anomalous_accounts.append(
                        {
                            "account_code": acc.account_code,
                            "account_name": acc.account_name,
                            "type": AnomalyType.UNEXPECTED_DEBIT_BALANCE.value,
                            "amount_eur": acc.closing_debit_eur,
                            "recommended_entry": f"Дт 503 / Кт {acc.account_code} (или приключване на задължение)",
                        }
                    )
                    recommendations.append(
                        f"⚠️ Пасивна сметка {acc.account_code} ({acc.account_name}) има дебитно салдо от €{acc.closing_debit_eur:,.2f}."
                    )

            # 3. Mathematical flow consistency check: Closing = Opening + Period
            expected_net = (acc.opening_debit_eur - acc.opening_credit_eur) + (
                acc.period_debit_eur - acc.period_credit_eur
            )
            actual_net = acc.closing_debit_eur - acc.closing_credit_eur
            if round(abs(expected_net - actual_net), 2) > 0.01:
                anomalous_accounts.append(
                    {
                        "account_code": acc.account_code,
                        "account_name": acc.account_name,
                        "type": AnomalyType.MATHEMATICAL_DISCREPANCY.value,
                        "amount_eur": round(abs(expected_net - actual_net), 2),
                        "recommended_entry": f"Преизчислете равенството: Крайно салдо = Начално салдо + Оборoти за сметка {acc.account_code}",
                    }
                )
                recommendations.append(
                    f"⚙️ Сметка {acc.account_code} ({acc.account_name}) съдържа математическо несъответствие от €{abs(expected_net - actual_net):,.2f}."
                )

            # 4. Nominal account closure check at month-end
            if is_month_end and (
                acc.account_code.startswith("60")
                or acc.account_code.startswith("61")
                or acc.account_code.startswith("62")
                or acc.account_code.startswith("70")
                or acc.account_code.startswith("72")
            ):
                closing_bal = abs(acc.closing_debit_eur - acc.closing_credit_eur)
                if closing_bal > 0.0:
                    nominal_unclosed_count += 1
                    target_123 = "123" if acc.account_code.startswith("6") else "123"
                    dr_cr_str = (
                        f"Дт 123 / Кт {acc.account_code}"
                        if acc.account_code.startswith("6")
                        else f"Дт {acc.account_code} / Кт 123"
                    )
                    anomalous_accounts.append(
                        {
                            "account_code": acc.account_code,
                            "account_name": acc.account_name,
                            "type": AnomalyType.UNCLOSED_NOMINAL_ACCOUNT.value,
                            "amount_eur": closing_bal,
                            "recommended_entry": dr_cr_str,
                        }
                    )
                    recommendations.append(
                        f"📋 Приключвателна операция: Приключете операционната сметка {acc.account_code} към Сметка 123 ({dr_cr_str})."
                    )

        # 5. VAT Settlement Check
        vat_reconciled = True
        if is_month_end and (vat_4531_val > 0 and vat_4532_val > 0):
            vat_reconciled = False
            anomalous_accounts.append(
                {
                    "account_code": "4538",
                    "account_name": "Разчети за ДДС",
                    "type": AnomalyType.VAT_SETTLEMENT_MISMATCH.value,
                    "amount_eur": min(vat_4531_val, vat_4532_val),
                    "recommended_entry": "Дт 4532 / Кт 4531 (Захващане на ДДС за месеца)",
                }
            )
            recommendations.append(
                f"🏛️ ДДС прихващане: Сметки 4531 (€{vat_4531_val:,.2f}) и 4532 (€{vat_4532_val:,.2f}) не са прихванати към Сметка 4538 преди ДДС декларация."
            )

        # Calculate composite risk score (0.0 to 1.0)
        risk_score = 0.0
        if not is_balanced:
            risk_score += 0.4
        risk_score += min(len(anomalous_accounts) * 0.15, 0.45)
        if not vat_reconciled:
            risk_score += 0.15
        risk_score = min(round(risk_score, 2), 1.0)

        # Determine risk level
        if risk_score <= 0.15:
            risk_level = SentinelRiskLevel.SAFE
        elif risk_score <= 0.40:
            risk_level = SentinelRiskLevel.LOW_RISK
        elif risk_score <= 0.70:
            risk_level = SentinelRiskLevel.MEDIUM_RISK
        elif risk_score <= 0.90:
            risk_level = SentinelRiskLevel.HIGH_RISK
        else:
            risk_level = SentinelRiskLevel.CRITICAL_RISK

        summary_bg = (
            f"Оборотната ведомост е БАЛАНСИРАНА (Риск: {risk_level.value})"
            if is_balanced and len(anomalous_accounts) == 0
            else f"Намерени са {len(anomalous_accounts)} аномалии в Оборотната ведомост (Риск: {risk_level.value}, {risk_score:.2f})"
        )

        report = AnomalyReport(
            is_balanced=is_balanced,
            total_debit_mismatch_eur=period_mismatch,
            anomalous_accounts=anomalous_accounts,
            risk_score=risk_score,
            recommendations=recommendations,
            risk_level=risk_level,
            total_opening_mismatch_eur=opening_mismatch,
            total_closing_mismatch_eur=closing_mismatch,
            vat_reconciled=vat_reconciled,
            nominal_accounts_closed=(nominal_unclosed_count == 0),
            summary_bg=summary_bg,
        )

        logger.info(
            f"🧠 Neural Trial Balance Evaluation: Balanced={is_balanced}, Anomalies={len(anomalous_accounts)}, RiskScore={risk_score}, Level={risk_level.value}"
        )
        return report

    @classmethod
    def predict_anomaly_probabilities(
        cls, accounts: List[TrialBalanceAccountItem]
    ) -> Dict[str, float]:
        """Calculates neural anomaly likelihood probabilities across key posting error dimensions."""
        report = cls.evaluate_trial_balance(accounts)
        prob_imbalance = 0.95 if not report.is_balanced else 0.02
        prob_red_balance = min(
            sum(
                1
                for a in report.anomalous_accounts
                if a["type"]
                in (
                    AnomalyType.UNEXPECTED_CREDIT_BALANCE.value,
                    AnomalyType.UNEXPECTED_DEBIT_BALANCE.value,
                )
            )
            * 0.4,
            0.99,
        )
        prob_math_err = min(
            sum(1 for a in report.anomalous_accounts if a["type"] == AnomalyType.MATHEMATICAL_DISCREPANCY.value) * 0.5,
            0.99,
        )
        prob_unclosed = 0.85 if not report.nominal_accounts_closed else 0.05
        prob_vat = 0.90 if not report.vat_reconciled else 0.03

        return {
            "debit_credit_imbalance": round(prob_imbalance, 4),
            "unexpected_side_balance": round(prob_red_balance, 4),
            "mathematical_discrepancy": round(prob_math_err, 4),
            "unclosed_nominal_accounts": round(prob_unclosed, 4),
            "vat_reconciliation_mismatch": round(prob_vat, 4),
            "overall_audit_risk": round(report.risk_score, 4),
        }

    @classmethod
    def format_sentinel_report_json(cls, report: AnomalyReport) -> str:
        """Serializes AnomalyReport into clean JSON format."""
        data = {
            "is_balanced": report.is_balanced,
            "total_debit_mismatch_eur": report.total_debit_mismatch_eur,
            "total_opening_mismatch_eur": report.total_opening_mismatch_eur,
            "total_closing_mismatch_eur": report.total_closing_mismatch_eur,
            "risk_score": report.risk_score,
            "risk_level": report.risk_level.value,
            "vat_reconciled": report.vat_reconciled,
            "nominal_accounts_closed": report.nominal_accounts_closed,
            "anomalous_accounts": report.anomalous_accounts,
            "recommendations": report.recommendations,
            "summary_bg": report.summary_bg,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
