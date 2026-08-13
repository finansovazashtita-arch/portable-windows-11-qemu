"""
Automated Real-Time Bank Account Reconciliation Guard (Bank Feed Guard).

Performs continuous sub-second reconciliation of live bank statement feeds against Account 503 ("Разплащателна сметка"):
- Real-time matching of incoming/outgoing bank transactions against booked ledger entries
- Automated detection and classification of unposted bank fees (creates Debit 621 "Разходи за банкови услуги" / Credit 503 proposals)
- Unposted customer/supplier transaction alert flagging
- Real-time bank feed balance vs. ledger Account 503 balance discrepancy guard
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("bank_feed_guard")


class BankFeedStatus(str, enum.Enum):
    MATCHED = "MATCHED"  # Успешно засечена транзакция
    UNPOSTED_TRANSFER = "UNPOSTED_TRANSFER"  # Неотчетен банков превод
    UNPOSTED_BANK_FEE = "UNPOSTED_BANK_FEE"  # Неотчетена банкова такса (Сметка 621)
    DISCREPANCY = "DISCREPANCY"  # Разхождение в сумата/баланса


@dataclasses.dataclass
class BankFeedItem:
    """Dataclass holding a single bank statement feed item."""

    transaction_id: str
    date: str
    amount_eur: float
    is_debit: bool  # True for outgoing/debit, False for incoming/credit
    narrative: str
    status: BankFeedStatus = BankFeedStatus.UNPOSTED_TRANSFER


@dataclasses.dataclass
class ReconciliationSummary:
    """Dataclass holding real-time bank account reconciliation results."""

    bank_closing_balance_eur: float
    ledger_503_balance_eur: float
    variance_eur: float
    matched_count: int
    unposted_transfers_count: int
    unposted_bank_fees_count: int
    proposed_fee_entries: List[Dict[str, Any]]


class BankFeedGuard:
    """Real-time bank feed reconciliation guard engine."""

    FEE_KEYWORDS = ["такса", "комисионна", "банкова такса", "bank fee", "commission", "charge", "maintenance fee"]

    @classmethod
    def reconcile_feed_item(
        cls, bank_item: BankFeedItem, ledger_503_entries: List[Dict[str, Any]]
    ) -> BankFeedItem:
        """Reconciles a single bank feed item against Account 503 ledger entries."""
        narrative_lower = bank_item.narrative.lower()

        # Check for exact ledger match
        for entry in ledger_503_entries:
            entry_amount = float(entry.get("amount_eur", 0.0))
            if abs(entry_amount - bank_item.amount_eur) < 0.01:
                bank_item.status = BankFeedStatus.MATCHED
                return bank_item

        # Check if item is an unposted bank fee
        if any(kw in narrative_lower for kw in cls.FEE_KEYWORDS):
            bank_item.status = BankFeedStatus.UNPOSTED_BANK_FEE
        else:
            bank_item.status = BankFeedStatus.UNPOSTED_TRANSFER

        return bank_item

    @classmethod
    def run_realtime_guard(
        cls,
        bank_items: List[BankFeedItem],
        ledger_503_entries: List[Dict[str, Any]],
        bank_opening_balance: float = 0.0,
        ledger_opening_balance: float = 0.0,
    ) -> ReconciliationSummary:
        """Runs continuous real-time reconciliation guard on all bank feed items."""
        matched_count = 0
        unposted_transfers = 0
        unposted_fees = 0
        proposed_fee_entries: List[Dict[str, Any]] = []

        bank_balance = bank_opening_balance
        ledger_balance = ledger_opening_balance + sum(
            float(e.get("amount_eur", 0.0)) if e.get("is_credit", False) else -float(e.get("amount_eur", 0.0))
            for e in ledger_503_entries
        )

        for item in bank_items:
            # Update running bank balance
            if item.is_debit:
                bank_balance -= item.amount_eur
            else:
                bank_balance += item.amount_eur

            reconciled_item = cls.reconcile_feed_item(item, ledger_503_entries)
            if reconciled_item.status == BankFeedStatus.MATCHED:
                matched_count += 1
            elif reconciled_item.status == BankFeedStatus.UNPOSTED_BANK_FEE:
                unposted_fees += 1
                proposed_fee_entries.append(
                    {
                        "date": item.date,
                        "document_number": f"FEE_{item.transaction_id}",
                        "narrative": item.narrative,
                        "debit_account": "621",  # Expenses for bank services / Разходи за банкови услуги
                        "debit_name": "Разходи за банкови услуги",
                        "credit_account": "503",  # Bank account / Разплащателна сметка
                        "credit_name": "Разплащателна сметка в EUR",
                        "amount_eur": item.amount_eur,
                    }
                )
            else:
                unposted_transfers += 1

        variance = round(bank_balance - ledger_balance, 2)
        summary = ReconciliationSummary(
            bank_closing_balance_eur=round(bank_balance, 2),
            ledger_503_balance_eur=round(ledger_balance, 2),
            variance_eur=variance,
            matched_count=matched_count,
            unposted_transfers_count=unposted_transfers,
            unposted_bank_fees_count=unposted_fees,
            proposed_fee_entries=proposed_fee_entries,
        )

        logger.info(
            f"🏦 Bank Feed Guard: Matched={matched_count}, Unposted Transfers={unposted_transfers}, "
            f"Unposted Fees={unposted_fees}, Variance=€{variance:,.2f}"
        )
        return summary
