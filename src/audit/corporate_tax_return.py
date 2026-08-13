"""
Autonomous Corporate Income Tax (CITA / ЗКПО) Tax Return Generator.

Computes statutory annual Bulgarian corporate income tax under Art. 92 CITA (Чл. 92 ЗКПО):
- Financial result adjustment (Account 609 non-deductible expenses, tax depreciation differences)
- 10% flat corporate tax rate calculation on taxable profit
- Double-entry accounting entries: Corporate Tax Expense (Account 123 / Account 454 "Разчети за данък върху печалбата")
- Statutory NRA annual tax return export
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List

logger = logging.getLogger("corporate_tax_return")


class TaxableAdjustmentType(str, enum.Enum):
    NON_DEDUCTIBLE_EXPENSE = "NON_DEDUCTIBLE_EXPENSE"  # Сметка 609 / Чл. 26 ЗКПО
    TAX_DEPRECIATION_DIFFERENCE = "TAX_DEPRECIATION_DIFFERENCE"  # Чл. 54 ЗКПО
    EXEMPT_INCOME = "EXEMPT_INCOME"  # Необлагаеми приходи


@dataclasses.dataclass
class AnnualTaxableAdjustment:
    """Dataclass holding tax result adjustment line items."""

    description: str
    adjustment_type: TaxableAdjustmentType
    amount_eur: float


@dataclasses.dataclass
class CorporateTaxReturn:
    """Dataclass holding annual CITA corporate tax calculation outcome."""

    year: int
    accounting_profit_eur: float
    total_increases_eur: float
    total_decreases_eur: float
    taxable_profit_eur: float
    corporate_tax_rate_percent: float
    corporate_tax_due_eur: float


class CorporateTaxReturnGenerator:
    """Generator for Bulgarian CITA (ЗКПО) annual tax returns and tax accounting entries."""

    @classmethod
    def calculate_corporate_tax(
        cls,
        year: int,
        accounting_profit_eur: float,
        adjustments: List[AnnualTaxableAdjustment],
        tax_rate_percent: float = 10.0,
    ) -> CorporateTaxReturn:
        """Calculates taxable profit and 10% CITA corporate income tax due."""
        total_inc = sum(a.amount_eur for a in adjustments if a.adjustment_type in (
            TaxableAdjustmentType.NON_DEDUCTIBLE_EXPENSE,
            TaxableAdjustmentType.TAX_DEPRECIATION_DIFFERENCE,
        ))
        total_dec = sum(a.amount_eur for a in adjustments if a.adjustment_type == TaxableAdjustmentType.EXEMPT_INCOME)

        taxable_profit = max(0.0, round(accounting_profit_eur + total_inc - total_dec, 2))
        tax_due = round(taxable_profit * (tax_rate_percent / 100.0), 2)

        tax_return = CorporateTaxReturn(
            year=year,
            accounting_profit_eur=accounting_profit_eur,
            total_increases_eur=round(total_inc, 2),
            total_decreases_eur=round(total_dec, 2),
            taxable_profit_eur=taxable_profit,
            corporate_tax_rate_percent=tax_rate_percent,
            corporate_tax_due_eur=tax_due,
        )
        logger.info(f"🏛️ CITA Corporate Tax [{year}]: Accounting Profit=€{accounting_profit_eur:,.2f}, Taxable=€{taxable_profit:,.2f}, Tax Due ({tax_rate_percent}%)=€{tax_due:,.2f}")
        return tax_return

    @classmethod
    def generate_corporate_tax_journal_entries(cls, tax_return: CorporateTaxReturn) -> List[Dict[str, Any]]:
        """Generates corporate tax accounting entries (Debit 123 / Credit 454)."""
        if tax_return.corporate_tax_due_eur <= 0:
            return []

        entries = [
            {
                "date": f"{tax_return.year}-12-31",
                "document_number": f"TAX_CITA_{tax_return.year}",
                "narrative": f"Начислен корпоративен данък върху печалбата по ЗКПО за {tax_return.year} г.",
                "debit_account": "123",  # Financial result for current year / Печалби и загуби
                "debit_name": "Печалби и загуби от текущата година",
                "credit_account": "454",  # Corporate tax payable / Разчети за корпоративен данък
                "credit_name": "Разчети за данък върху печалбата",
                "amount_eur": tax_return.corporate_tax_due_eur,
            }
        ]
        return entries
