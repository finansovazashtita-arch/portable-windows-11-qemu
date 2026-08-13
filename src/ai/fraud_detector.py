"""
AI Fraud Prevention & Anomaly Detection Guardrail Engine.

Supports:
- Unverified/changed IBAN detection vs vendor history
- Cross-bank duplicate invoice detection
- Monetary amount spike anomalies
- Suspicious narrative keyword flagging
"""

import dataclasses
import enum
import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("fraud_detector")


class AnomalyRiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FraudFlag(str, enum.Enum):
    UNVERIFIED_IBAN = "UNVERIFIED_IBAN"
    CROSS_BANK_DUPLICATE = "CROSS_BANK_DUPLICATE"
    MONETARY_SPIKE = "MONETARY_SPIKE"
    SUSPICIOUS_KEYWORD = "SUSPICIOUS_KEYWORD"


SUSPICIOUS_KEYWORDS = {
    "КРИПТО",
    "CRYPTO",
    "КАЗИНО",
    "CASINO",
    "ZALAGAONICA",
    "ЗАЛОЖНА КЪЩА",
    "ЛИЧНА СМЕТКА",
    "TEGLENE NA BROI",
}


@dataclasses.dataclass
class TransactionRiskEvaluation:
    """Dataclass holding transaction risk evaluation outcome."""

    item_id: int
    risk_score: float  # 0.0 to 1.0
    risk_level: AnomalyRiskLevel
    flags: List[str]
    recommendation: str


FraudRiskAssessment = TransactionRiskEvaluation


class FraudGuardrailEngine:
    """Evaluates transaction risk against security guardrails and historical trends."""

    def __init__(self, known_partner_ibans: Optional[Dict[str, str]] = None):
        # Mapping of partner name/EIK -> expected IBAN
        self.known_partner_ibans = known_partner_ibans or {
            "СТОРГОЗИЯ АД": "BG71STSA93000028013479",
            "ПЛЕВЕН СТРОЙ ЕООД": "BG77BPBI91001122334455",
        }

    def evaluate_transaction(
        self, tx: Dict[str, Any], history: Optional[List[Dict[str, Any]]] = None
    ) -> TransactionRiskEvaluation:
        """Evaluates a single transaction dictionary against fraud guardrails."""
        flags: List[str] = []
        score = 0.0
        item_id = tx.get("item_id", 0)
        narrative = (tx.get("narrative_description") or tx.get("counterparty_name") or "").upper()
        cp_name = (tx.get("counterparty_name") or "").upper()
        cp_iban = (tx.get("counterparty_iban") or "").replace(" ", "").upper()

        amount = float(tx.get("debit_amount", 0.0)) or float(tx.get("credit_amount", 0.0))

        # Guardrail 1: Suspicious Keyword Check
        for kw in SUSPICIOUS_KEYWORDS:
            if kw in narrative:
                flags.append(FraudFlag.SUSPICIOUS_KEYWORD.value)
                score += 0.40
                break

        # Guardrail 2: Unverified IBAN Check
        if cp_name in self.known_partner_ibans:
            expected = self.known_partner_ibans[cp_name].replace(" ", "").upper()
            if cp_iban and cp_iban != expected:
                flags.append(FraudFlag.UNVERIFIED_IBAN.value)
                score += 0.50

        # Guardrail 3: Monetary Amount Spike Check (> €10,000 or 5x history avg)
        if history:
            amounts = [
                float(h.get("debit_amount", 0.0)) or float(h.get("credit_amount", 0.0))
                for h in history
                if (h.get("counterparty_name") or "").upper() == cp_name
            ]
            if amounts:
                avg_amt = sum(amounts) / len(amounts)
                if avg_amt > 0 and amount > (avg_amt * 5.0):
                    flags.append(FraudFlag.MONETARY_SPIKE.value)
                    score += 0.35
        elif amount > 50000.0:
            flags.append(FraudFlag.MONETARY_SPIKE.value)
            score += 0.30

        # Risk level determination
        score = min(round(score, 2), 1.0)
        if score >= 0.70:
            level = AnomalyRiskLevel.CRITICAL if score >= 0.85 else AnomalyRiskLevel.HIGH
            recommendation = "🛑 БЛОКИРАЙ: Изисква се ръчно преглеждане от главен счетоводител!"
        elif score >= 0.30:
            level = AnomalyRiskLevel.MEDIUM
            recommendation = "⚠️ ВНИМАНИЕ: Препоръчва се верификация на IBAN / основание!"
        else:
            level = AnomalyRiskLevel.LOW
            recommendation = "✅ ОДОБРЕНО: Нисък риск, автоматичен импорт."

        return TransactionRiskEvaluation(
            item_id=item_id,
            risk_score=score,
            risk_level=level,
            flags=flags,
            recommendation=recommendation,
        )

    def evaluate_batch(
        self, transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enriches batch transactions with fraud risk evaluations and flags cross-bank duplicates."""
        seen_docs: Set[str] = set()
        enriched = []

        for tx in transactions:
            tx_copy = dict(tx)
            eval_res = self.evaluate_transaction(tx, history=transactions)

            doc_num = tx.get("document_number", "").strip()
            if doc_num and doc_num in seen_docs:
                eval_res.flags.append(FraudFlag.CROSS_BANK_DUPLICATE.value)
                eval_res.risk_score = min(eval_res.risk_score + 0.50, 1.0)
                eval_res.risk_level = AnomalyRiskLevel.CRITICAL
                eval_res.recommendation = "🛑 БЛОКИРАЙ: Открит дублиран документ в друг поток!"

            if doc_num:
                seen_docs.add(doc_num)

            tx_copy["risk_score"] = eval_res.risk_score
            tx_copy["risk_level"] = eval_res.risk_level.value
            tx_copy["fraud_flags"] = eval_res.flags
            tx_copy["risk_recommendation"] = eval_res.recommendation
            enriched.append(tx_copy)

        return enriched
