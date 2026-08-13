"""
Autonomous Cash Desk & Petty Cash Management Engine (Account 501 / ПКО & РКО).

Manages statutory Bulgarian cash desk operations:
- Cash Receipt Orders (Приходен Касов Ордер / ПКО) - Debit Account 501 ("Каса в EUR/BGN")
- Cash Expense Orders (Разходен Касов Ордер / РКО) - Credit Account 501 ("Каса в EUR/BGN")
- Daily cash book reconciliation and balance tracking
- Cash limit monitoring (alert on exceeding statutory/company cash threshold)
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List

logger = logging.getLogger("cash_desk_manager")


class CashOrderType(str, enum.Enum):
    RECEIPT_ORDER = "RECEIPT_ORDER"  # Приходен касов ордер (ПКО)
    EXPENSE_ORDER = "EXPENSE_ORDER"  # Разходен касов ордер (РКО)


@dataclasses.dataclass
class CashOrder:
    """Dataclass holding a single cash receipt or expense order."""

    order_id: str
    date: str
    order_type: CashOrderType
    amount_eur: float
    counterparty_name: str
    counterparty_account: str  # e.g., "411" for customer, "401" for supplier, "503" for bank withdrawal
    narrative: str


@dataclasses.dataclass
class CashDeskSummary:
    """Dataclass holding daily cash book summary results."""

    date: str
    opening_balance_eur: float
    total_receipts_eur: float
    total_expenses_eur: float
    closing_balance_eur: float
    cash_limit_eur: float
    limit_exceeded_flag: bool
    journal_entries: List[Dict[str, Any]]


class CashDeskManager:
    """Manager for petty cash desk accounting, PKO/RKO generation, and cash book reconciliation."""

    @classmethod
    def process_cash_order(cls, order: CashOrder) -> Dict[str, Any]:
        """Generates double-entry accounting entry for a single cash order."""
        if order.order_type == CashOrderType.RECEIPT_ORDER:
            # PKO: Debit 501 / Credit Counterparty Account
            entry = {
                "date": order.date,
                "document_number": f"PKO_{order.order_id}",
                "narrative": f"ПКО: {order.narrative} ({order.counterparty_name})",
                "debit_account": "501",  # Cash account / Каса в EUR
                "debit_name": "Каса в EUR",
                "credit_account": order.counterparty_account,
                "credit_name": f"Сметка {order.counterparty_account}",
                "amount_eur": order.amount_eur,
            }
        else:
            # RKO: Debit Counterparty Account / Credit 501
            entry = {
                "date": order.date,
                "document_number": f"RKO_{order.order_id}",
                "narrative": f"РКО: {order.narrative} ({order.counterparty_name})",
                "debit_account": order.counterparty_account,
                "debit_name": f"Сметка {order.counterparty_account}",
                "credit_account": "501",  # Cash account / Каса в EUR
                "credit_name": "Каса в EUR",
                "amount_eur": order.amount_eur,
            }

        logger.info(f"💵 Cash Order [{order.order_type.value} - {order.order_id}]: €{order.amount_eur:,.2f} ({order.narrative})")
        return entry

    @classmethod
    def generate_daily_cash_book(
        cls,
        date_str: str,
        orders: List[CashOrder],
        opening_balance_eur: float = 0.0,
        cash_limit_eur: float = 5000.0,
    ) -> CashDeskSummary:
        """Reconciles daily cash book, generates journal entries, and checks cash limits."""
        total_receipts = 0.0
        total_expenses = 0.0
        journal_entries: List[Dict[str, Any]] = []

        for order in orders:
            entry = cls.process_cash_order(order)
            journal_entries.append(entry)
            if order.order_type == CashOrderType.RECEIPT_ORDER:
                total_receipts += order.amount_eur
            else:
                total_expenses += order.amount_eur

        closing_balance = round(opening_balance_eur + total_receipts - total_expenses, 2)
        limit_exceeded = closing_balance > cash_limit_eur

        if limit_exceeded:
            logger.warning(
                f"⚠️ Cash Limit Exceeded [{date_str}]: Closing Balance €{closing_balance:,.2f} exceeds limit €{cash_limit_eur:,.2f}"
            )

        summary = CashDeskSummary(
            date=date_str,
            opening_balance_eur=opening_balance_eur,
            total_receipts_eur=round(total_receipts, 2),
            total_expenses_eur=round(total_expenses, 2),
            closing_balance_eur=closing_balance,
            cash_limit_eur=cash_limit_eur,
            limit_exceeded_flag=limit_exceeded,
            journal_entries=journal_entries,
        )
        return summary
