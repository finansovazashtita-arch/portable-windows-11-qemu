"""
Autonomous Business Travel Expenses & Per Diem Allowance Manager (Account 609 / Наредба за командировките).

Manages statutory Bulgarian travel expense processing and per diem calculations:
- Domestic & International business travel allowance computation under Bulgarian Travel Regulations (Наредба за командировките в страната и чужбина)
- Accounting entries: Debit Account 609 ("Други разходи / Разходи за командировки") / Credit Account 422 ("Под отчетни лица") or Account 501/503
- Statutory travel order expense summary generation
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List

logger = logging.getLogger("travel_expense_manager")


class TravelType(str, enum.Enum):
    DOMESTIC = "DOMESTIC"  # Командировка в страната (20 EUR / 40 BGN дневно)
    INTERNATIONAL = "INTERNATIONAL"  # Командировка в чужбина (50 EUR дневно)


@dataclasses.dataclass
class BusinessTravelOrder:
    """Dataclass holding a business travel order and expense claims."""

    order_id: str
    employee_name: str
    destination: str
    travel_type: TravelType
    days_count: int
    per_diem_daily_rate_eur: float
    lodging_total_eur: float
    transport_total_eur: float
    start_date: str = "2026-06-01"


@dataclasses.dataclass
class BusinessTravelReport:
    """Dataclass holding completed travel expense calculations and accounting entries."""

    order_id: str
    employee_name: str
    total_per_diem_eur: float
    total_lodging_eur: float
    total_transport_eur: float
    total_travel_expense_eur: float
    journal_entries: List[Dict[str, Any]]


class TravelExpenseManager:
    """Manager for business travel expenses and per diem allowances."""

    @classmethod
    def process_travel_order(
        cls, order: BusinessTravelOrder, payment_account: str = "422"
    ) -> BusinessTravelReport:
        """Calculates total travel costs and generates statutory accounting entries."""
        total_per_diem = round(order.days_count * order.per_diem_daily_rate_eur, 2)
        total_expense = round(total_per_diem + order.lodging_total_eur + order.transport_total_eur, 2)

        entries = [
            {
                "date": order.start_date,
                "document_number": f"TRAVEL_{order.order_id}",
                "narrative": f"Отчетени командировъчни разходи (дневни + квартирни + пътни) за {order.employee_name} ({order.destination})",
                "debit_account": "609",  # Other expenses / Разходи за командировки
                "debit_name": "Разходи за командировки",
                "credit_account": payment_account,  # Accounts payable / Podotcheti litsa
                "credit_name": f"Сметка {payment_account}",
                "amount_eur": total_expense,
            }
        ]

        report = BusinessTravelReport(
            order_id=order.order_id,
            employee_name=order.employee_name,
            total_per_diem_eur=total_per_diem,
            total_lodging_eur=round(order.lodging_total_eur, 2),
            total_transport_eur=round(order.transport_total_eur, 2),
            total_travel_expense_eur=total_expense,
            journal_entries=entries,
        )

        logger.info(
            f"✈️ Business Travel Order [{order.order_id}]: {order.employee_name} ({order.destination}) = "
            f"Per Diem: €{total_per_diem:,.2f}, Total: €{total_expense:,.2f}"
        )
        return report
