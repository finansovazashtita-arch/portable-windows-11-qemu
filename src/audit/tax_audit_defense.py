"""
Autonomous Tax Audit Defense & Discrepancy Risk Scoring Engine (чл. 92 ЗДДС & НАП Одит).

Evaluates tax filing data against statutory Bulgarian National Revenue Agency (НАП) audit indicators:
- VAT Refund Audit Risk Assessment (Art. 92 VATA / Чл. 92 ЗДДС)
- Missing tax invoice discrepancy detection
- VIES/NRA Deregistered counterparty warning flags
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tax_audit_defense")


class AuditRiskLevel(str, enum.Enum):
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_AUDIT_RISK = "HIGH_AUDIT_RISK"


@dataclasses.dataclass
class AuditDefenseEvaluation:
    """Dataclass holding tax audit risk assessment results."""

    overall_risk_score: float
    risk_level: AuditRiskLevel
    art92_vat_refund_flag: bool
    missing_invoices_count: int
    deregistered_vat_counterparties: List[str]
    audit_warnings_bg: List[str]


class TaxAuditDefenseEngine:
    """Engine analyzing tax audit risk indicators before NRA VAT filing."""

    @classmethod
    def evaluate_audit_risk(
        cls,
        vat_refundable_amount: float,
        vat_payable_amount: float,
        purchase_invoices: List[Dict[str, Any]],
        sales_invoices: List[Dict[str, Any]],
        known_deregistered_eiks: Optional[List[str]] = None,
    ) -> AuditDefenseEvaluation:
        """Evaluates NRA tax audit risk triggers."""
        known_deregistered = set(known_deregistered_eiks or [])
        warnings = []
        risk_score = 10.0
        deregistered_found = []
        missing_inv_count = 0

        # 1. Art. 92 VATA VAT Refund Check (Чл. 92 ЗДДС)
        art92_flag = False
        if vat_refundable_amount > 5000.0:
            art92_flag = True
            risk_score += 35.0
            warnings.append(
                f"⚠️ Чл. 92 ЗДДС: ДДС за възстановяване ({vat_refundable_amount:.2f} лв.) надвишава прага от 5,000 лв. "
                "Висок риск от ревизия/проверка от НАП."
            )

        # 2. Check for missing tax invoice numbers
        for idx, inv in enumerate(purchase_invoices, 1):
            if not inv.get("doc_num") or str(inv.get("doc_num")).strip() == "":
                missing_inv_count += 1
                risk_score += 15.0
                warnings.append(f"❌ Липсва номер на фактура за покупка на ред #{idx}.")

        # 3. Check for deregistered VAT counterparties
        for inv in purchase_invoices + sales_invoices:
            eik = str(inv.get("supplier_eik") or inv.get("client_eik") or "").strip()
            if eik in known_deregistered and eik not in deregistered_found:
                deregistered_found.append(eik)
                risk_score += 25.0
                warnings.append(f"⛔ Контрагент с ЕИК [{eik}] е де-регистриран по ДДС! Данъчният кредит ще бъде отказан.")

        risk_score = min(100.0, risk_score)
        if risk_score >= 60.0:
            risk_level = AuditRiskLevel.HIGH_AUDIT_RISK
        elif risk_score >= 30.0:
            risk_level = AuditRiskLevel.MEDIUM_RISK
        else:
            risk_level = AuditRiskLevel.LOW_RISK

        evaluation = AuditDefenseEvaluation(
            overall_risk_score=round(risk_score, 1),
            risk_level=risk_level,
            art92_vat_refund_flag=art92_flag,
            missing_invoices_count=missing_inv_count,
            deregistered_vat_counterparties=deregistered_found,
            audit_warnings_bg=warnings,
        )
        logger.info(f"🛡️ Tax Audit Defense Evaluation: Risk Score = {risk_score}/100 ({risk_level.value})")
        return evaluation
