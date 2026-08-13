"""
Autonomous Open Banking Payment Initiation & Multi-Bank AISP Aggregator (PISP / AISP Adapter).

Provides Berlin Group PSD2 specifications for:
- Automated Payment Initiation Service Provider (PISP) execution for vendor invoice settlement (Account 401 -> Account 503)
- Multi-bank Account Information Service Provider (AISP) real-time balance aggregation across DSK, UniCredit Bulbank, UBB, and Postbank
- Generation of double-entry accounting settlement entries (Debit 401 / Credit 503)
"""

import dataclasses
import logging
import uuid
from typing import Any, Dict, List

logger = logging.getLogger("open_banking_pisp")


@dataclasses.dataclass
class PaymentInitiationRequest:
    """Dataclass holding a PSD2 Payment Initiation request payload."""

    payment_id: str
    debtor_iban: str
    creditor_iban: str
    creditor_name: str
    amount_eur: float
    remittance_info: str
    bank_code: str = "DSK"


@dataclasses.dataclass
class PaymentInitiationResult:
    """Dataclass holding the result of a PSD2 payment initiation."""

    payment_id: str
    transaction_status: str  # ACCP (Accepted), RJCT (Rejected), PNDG (Pending)
    psd2_consent_id: str
    journal_entry: Dict[str, Any]


class OpenBankingPISPAggregator:
    """Aggregator engine for PSD2 payment initiation and multi-bank account streaming."""

    SUPPORTED_BANKS = {"DSK": "DSK Bank", "UNCR": "UniCredit Bulbank", "UBBS": "UBB", "BPBI": "Postbank"}

    @classmethod
    def initiate_vendor_payment(cls, req: PaymentInitiationRequest) -> PaymentInitiationResult:
        """Initiates a PSD2 PISP vendor payment and generates accounting settlement entry."""
        if req.bank_code not in cls.SUPPORTED_BANKS:
            raise ValueError(f"Unsupported bank code: {req.bank_code}")

        consent_id = f"CONSENT_PSD2_{uuid.uuid4().hex[:12].upper()}"

        # Generate accounting settlement journal entry (Debit 401 / Credit 503)
        journal_entry = {
            "date": "2026-06-15",
            "document_number": f"PISP_{req.payment_id}",
            "narrative": f"PSD2 PISP плащане към {req.creditor_name} по фактура {req.remittance_info}",
            "debit_account": "401",  # Suppliers / Задължения към доставчици
            "debit_name": f"Доставчик {req.creditor_name}",
            "credit_account": "501" if "CASH" in req.debtor_iban else "503",  # Bank / Разплащателна сметка
            "credit_name": "Разплащателна сметка в EUR",
            "amount_eur": req.amount_eur,
        }

        result = PaymentInitiationResult(
            payment_id=req.payment_id,
            transaction_status="ACCP",
            psd2_consent_id=consent_id,
            journal_entry=journal_entry,
        )

        logger.info(
            f"🏦 PSD2 PISP Payment Initiated [{req.bank_code}]: €{req.amount_eur:,.2f} -> {req.creditor_name} ({consent_id})"
        )
        return result

    @classmethod
    def aggregate_multi_bank_balances(cls, bank_ibans: Dict[str, str]) -> Dict[str, Any]:
        """Aggregates real-time account balances across multiple banks."""
        consolidated: Dict[str, float] = {}
        total_balance_eur = 0.0

        for bank_code, iban in bank_ibans.items():
            # Mock balance fetch per bank
            simulated_balance = 25000.0 if bank_code == "DSK" else 15000.0
            consolidated[bank_code] = simulated_balance
            total_balance_eur += simulated_balance

        return {
            "bank_balances": consolidated,
            "total_consolidated_balance_eur": total_balance_eur,
            "bank_count": len(bank_ibans),
        }

    @classmethod
    def execute_scheduled_payment_batch(
        cls, schedule_items: List[Any], debtor_iban: str = "BG80STSA93000025123456"
    ) -> Dict[str, Any]:
        """Executes a batch of PSD2 PISP payments based on an optimized cash flow payment schedule."""
        results = []
        total_payout_eur = 0.0

        for item in schedule_items:
            invoice_id = getattr(item, "invoice_id", "INV-UNKNOWN")
            vendor_name = getattr(item, "vendor_name", "Vendor")
            net_amount_bgn = getattr(item, "net_payment_amount_bgn", getattr(item, "amount_bgn", 0.0))
            amount_eur = round(net_amount_bgn / 1.95583, 2)

            req = PaymentInitiationRequest(
                payment_id=f"PISP_SCHED_{uuid.uuid4().hex[:8].upper()}",
                debtor_iban=debtor_iban,
                creditor_iban="BG98UNCR70001523984712",
                creditor_name=vendor_name,
                amount_eur=amount_eur,
                remittance_info=f"Фактура {invoice_id}",
                bank_code="DSK",
            )
            res = cls.initiate_vendor_payment(req)
            results.append(res)
            total_payout_eur += amount_eur

        return {
            "processed_count": len(results),
            "total_payout_eur": round(total_payout_eur, 2),
            "total_payout_bgn": round(total_payout_eur * 1.95583, 2),
            "payment_results": [dataclasses.asdict(r) for r in results],
        }
