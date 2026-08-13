"""
Autonomous Personal Income Tax & Dividend Withholding Tax Manager.

Computes statutory 5% dividend withholding tax under Art. 194 CITA (ЗКПО) & Art. 38 Personal Income Tax Act (ЗДДФЛ):
- Calculates 5% tax withholding for physical persons and non-EU foreign entities (0% for qualified EU corporate parents)
- Generates double-entry accounting entries (Debit 122 "Неразпределена печалба" / Credit 425 "Задължения за дивиденти" & Credit 454 "Данък дивиденти")
- Generates quarterly NRA Form 55 filing declaration summary (Декларация по чл. 55 ЗКПО / чл. 201 ЗДДФЛ)
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List

logger = logging.getLogger("dividend_tax_manager")


class DividendBeneficiaryType(str, enum.Enum):
    PHYSICAL_PERSON = "PHYSICAL_PERSON"  # Физическо лице (5% данък)
    FOREIGN_ENTITY = "FOREIGN_ENTITY"  # Чуждестранно юридическо лице (5% данък)
    EU_LEGAL_ENTITY = "EU_LEGAL_ENTITY"  # Юридическо лице от ЕС (0% данък по майчина директива)


@dataclasses.dataclass
class DividendPayout:
    """Dataclass holding dividend payout details and withholding tax."""

    payout_id: str
    shareholder_name: str
    beneficiary_type: DividendBeneficiaryType
    gross_dividend_eur: float
    withholding_tax_rate_percent: float
    withholding_tax_due_eur: float
    net_dividend_eur: float


class DividendTaxManager:
    """Manager for Bulgarian dividend withholding tax calculation and NRA Form 55 reporting."""

    @classmethod
    def process_dividend_payout(
        cls,
        payout_id: str,
        shareholder_name: str,
        beneficiary_type: DividendBeneficiaryType,
        gross_dividend_eur: float,
    ) -> DividendPayout:
        """Calculates 5% withholding tax and net dividend payout amount."""
        tax_rate = 0.0 if beneficiary_type == DividendBeneficiaryType.EU_LEGAL_ENTITY else 5.0
        tax_due = round(gross_dividend_eur * (tax_rate / 100.0), 2)
        net_dividend = round(gross_dividend_eur - tax_due, 2)

        payout = DividendPayout(
            payout_id=payout_id,
            shareholder_name=shareholder_name,
            beneficiary_type=beneficiary_type,
            gross_dividend_eur=gross_dividend_eur,
            withholding_tax_rate_percent=tax_rate,
            withholding_tax_due_eur=tax_due,
            net_dividend_eur=net_dividend,
        )
        logger.info(f"💰 Dividend Payout [{payout_id}]: {shareholder_name} ({beneficiary_type.value}) = Gross: €{gross_dividend_eur:,.2f}, Tax ({tax_rate}%): €{tax_due:,.2f}, Net: €{net_dividend:,.2f}")
        return payout

    @classmethod
    def generate_dividend_journal_entries(
        cls, payout: DividendPayout, date_str: str = "2026-06-30"
    ) -> List[Dict[str, Any]]:
        """Generates dividend distribution journal entries (Debit 122 / Credit 425 & 454)."""
        entries = []

        # 1. Net Dividend Liability to Shareholder: Debit 122 / Credit 425
        entries.append(
            {
                "date": date_str,
                "document_number": f"DIV_{payout.payout_id}",
                "narrative": f"Начислен дивидент за изплащане на {payout.shareholder_name}",
                "debit_account": "122",  # Retained earnings / Неразпределена печалба
                "debit_name": "Неразпределена печалба от минали години",
                "credit_account": "425",  # Dividends payable / Задължения за дивиденти
                "credit_name": "Задължения за дивиденти",
                "amount_eur": payout.net_dividend_eur,
            }
        )

        # 2. Withholding Dividend Tax Liability: Debit 122 / Credit 454
        if payout.withholding_tax_due_eur > 0:
            entries.append(
                {
                    "date": date_str,
                    "document_number": f"DIV_TAX_{payout.payout_id}",
                    "narrative": f"Удържан данък върху дивидента ({payout.withholding_tax_rate_percent}%) за {payout.shareholder_name}",
                    "debit_account": "122",  # Retained earnings / Неразпределена печалба
                    "debit_name": "Неразпределена печалба от минали години",
                    "credit_account": "454",  # Dividend tax / Разчети за данък върху дивидентите
                    "credit_name": "Данък върху дивидентите",
                    "amount_eur": payout.withholding_tax_due_eur,
                }
            )

        return entries

    @classmethod
    def generate_form55_declaration(
        cls, year: int, quarter_num: int, payouts: List[DividendPayout]
    ) -> Dict[str, Any]:
        """Generates quarterly NRA Form 55 declaration summary."""
        total_gross = sum(p.gross_dividend_eur for p in payouts)
        total_tax = sum(p.withholding_tax_due_eur for p in payouts)

        return {
            "declaration_type": "FORM_55_NRA",
            "year": year,
            "quarter": f"Q{quarter_num}",
            "payouts_count": len(payouts),
            "total_gross_dividends_eur": round(total_gross, 2),
            "total_withholding_tax_due_eur": round(total_tax, 2),
            "due_date": f"{year}-{(quarter_num * 3) + 1:02d}-31",
        }
