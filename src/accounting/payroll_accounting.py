"""
Automated Payroll & Social Security Ledger Integration Module.

Generates statutory Bulgarian double-entry accounting journal entries for monthly payrolls:
- Account 604 ("Разходи за заплати")
- Account 421 ("Персонал")
- Account 454 ("Данък върху доходите на физическите лица - ДДФЛ")
- Account 455 ("Осигурителни задължения - НОИ/ЗДРАВНО")
- Account 605 ("Разходи за социални осигуровки - Работодател")
- Account 503 ("Разплащателна сметка в EUR/BGN")
"""

import dataclasses
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger("payroll_accounting")


@dataclasses.dataclass
class PayrollSummary:
    """Dataclass holding Bulgarian payroll summary amounts."""

    gross_salaries: float
    employee_social_security: float
    employee_income_tax: float
    employer_social_security: float

    @property
    def net_salaries(self) -> float:
        return round(self.gross_salaries - self.employee_social_security - self.employee_income_tax, 2)

    @property
    def total_cost_for_company(self) -> float:
        return round(self.gross_salaries + self.employer_social_security, 2)


class PayrollProcessor:
    """Generates statutory Bulgarian double-entry payroll accounting entries."""

    @classmethod
    def generate_payroll_entries(
        cls, payroll: PayrollSummary, date_str: str = "2026-01-31"
    ) -> List[Dict[str, Any]]:
        """Generates full set of double-entry payroll entries maintaining D = C equilibrium."""
        entries = []

        # 1. Gross Salaries Expense: Debit 604 / Credit 421
        entries.append(
            {
                "date": date_str,
                "document_number": "PAY_01",
                "narrative": "Начислени възнаграждения за заплати на персонала",
                "debit_account": "604",
                "debit_name": "Разходи за заплати",
                "credit_account": "421",
                "credit_name": "Персонал",
                "amount": round(payroll.gross_salaries, 2),
            }
        )

        # 2. Employee Social Security Withholding: Debit 421 / Credit 455
        entries.append(
            {
                "date": date_str,
                "document_number": "PAY_02",
                "narrative": "Удържани лични осигуровки за сметка на работника",
                "debit_account": "421",
                "debit_name": "Персонал",
                "credit_account": "455",
                "credit_name": "Осигурителни задължения",
                "amount": round(payroll.employee_social_security, 2),
            }
        )

        # 3. Income Tax (DOD) Withholding: Debit 421 / Credit 454
        entries.append(
            {
                "date": date_str,
                "document_number": "PAY_03",
                "narrative": "Удържан данък върху доходите на физическите лица (ДДФЛ)",
                "debit_account": "421",
                "debit_name": "Персонал",
                "credit_account": "454",
                "credit_name": "Данъци върху дохода на физическите лица",
                "amount": round(payroll.employee_income_tax, 2),
            }
        )

        # 4. Employer Social Security Expense: Debit 605 / Credit 455
        entries.append(
            {
                "date": date_str,
                "document_number": "PAY_04",
                "narrative": "Начислени осигуровки за сметка на работодателя",
                "debit_account": "605",
                "debit_name": "Разходи за социални осигуровки",
                "credit_account": "455",
                "credit_name": "Осигурителни задължения",
                "amount": round(payroll.employer_social_security, 2),
            }
        )

        # 5. Net Salary Payment via Bank: Debit 421 / Credit 503
        entries.append(
            {
                "date": date_str,
                "document_number": "PAY_05",
                "narrative": "Изплатени чисти заплати по банкови сметки на персонала",
                "debit_account": "421",
                "debit_name": "Персонал",
                "credit_account": "503",
                "credit_name": "Разплащателна сметка",
                "amount": round(payroll.net_salaries, 2),
            }
        )

        logger.info(
            f"Generated {len(entries)} payroll accounting entries for gross €{payroll.gross_salaries:.2f} "
            f"(Net: €{payroll.net_salaries:.2f})"
        )

        return entries
