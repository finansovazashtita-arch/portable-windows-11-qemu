"""
Automated Customs & Excise Tax Accounting Engine.

Generates statutory Bulgarian double-entry journal entries for non-EU import declarations (ЕАД):
- Account 457 ("Разчети с митници - Мита и ДДС при внос")
- Account 458 ("Разчети за акцизи")
- Account 304 ("Стоки")
- Account 4531 ("Начислен данък за покупките - Вносен ДДС")
- Account 503 ("Разплащателна сметка")
"""

import dataclasses
import logging
from typing import Any, Dict, List

logger = logging.getLogger("customs_excise_accounting")


@dataclasses.dataclass
class CustomsDeclaration:
    """Dataclass holding customs import declaration amounts."""

    declaration_number: str
    inventory_value: float
    import_duty_amount: float
    excise_tax_amount: float
    import_vat_amount: float

    @property
    def total_customs_liabilities(self) -> float:
        return round(self.import_duty_amount + self.import_vat_amount, 2)


class CustomsExciseProcessor:
    """Generates statutory Bulgarian double-entry customs and excise tax journal entries."""

    @classmethod
    def generate_customs_entries(
        cls, decl: CustomsDeclaration, date_str: str = "2026-01-31"
    ) -> List[Dict[str, Any]]:
        """Generates full set of double-entry customs accounting entries."""
        entries = []

        # 1. Customs Duty on Imported Inventory: Debit 304 / Credit 457
        if decl.import_duty_amount > 0:
            entries.append(
                {
                    "date": date_str,
                    "document_number": f"CUST_{decl.declaration_number}",
                    "narrative": f"Начислено мито по ЕАД {decl.declaration_number} в стойността на стоките",
                    "debit_account": "304",
                    "debit_name": "Стоки",
                    "credit_account": "457",
                    "credit_name": "Разчети с митници",
                    "amount": round(decl.import_duty_amount, 2),
                }
            )

        # 2. Excise Tax on Imported Goods: Debit 304 / Credit 458
        if decl.excise_tax_amount > 0:
            entries.append(
                {
                    "date": date_str,
                    "document_number": f"EXC_{decl.declaration_number}",
                    "narrative": f"Начислен акциз по ЕАД {decl.declaration_number} в стойността на стоките",
                    "debit_account": "304",
                    "debit_name": "Стоки",
                    "credit_account": "458",
                    "credit_name": "Разчети за акцизи",
                    "amount": round(decl.excise_tax_amount, 2),
                }
            )

        # 3. Import VAT Paid to Customs: Debit 4531 / Credit 457
        if decl.import_vat_amount > 0:
            entries.append(
                {
                    "date": date_str,
                    "document_number": f"VAT_{decl.declaration_number}",
                    "narrative": f"Платен ДДС при внос по ЕАД {decl.declaration_number}",
                    "debit_account": "4531",
                    "debit_name": "Начислен данък за покупките",
                    "credit_account": "457",
                    "credit_name": "Разчети с митници",
                    "amount": round(decl.import_vat_amount, 2),
                }
            )

        # 4. Bank Settlement of Customs Obligations: Debit 457 / Credit 503
        if decl.total_customs_liabilities > 0:
            entries.append(
                {
                    "date": date_str,
                    "document_number": f"BANK_CUST_{decl.declaration_number}",
                    "narrative": f"Платени митнически задължения (мито + ДДС) по банкa",
                    "debit_account": "457",
                    "debit_name": "Разчети с митници",
                    "credit_account": "503",
                    "credit_name": "Разплащателна сметка",
                    "amount": decl.total_customs_liabilities,
                }
            )

        logger.info(f"Generated {len(entries)} customs/excise accounting entries for declaration {decl.declaration_number}")
        return entries
