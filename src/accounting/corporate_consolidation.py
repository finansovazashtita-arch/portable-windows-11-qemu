"""
Autonomous Multi-Entity Corporate Consolidation & Intercompany Elimination Engine.

Consolidates financial statements for corporate holding structures:
- Aggregates multi-subsidiary trial balances (Accounts 503, 401, 411, 702, 601, etc.)
- Automatically detects and eliminates intercompany receivables (Account 411 "Клиенти") and payables (Account 401 "Доставчици")
- Generates statutory elimination journal entries (Debit 401 / Credit 411)
"""

import dataclasses
import logging
from typing import Any, Dict, List

logger = logging.getLogger("corporate_consolidation")


@dataclasses.dataclass
class EntityFinancialTrialBalance:
    """Dataclass holding legal entity trial balance and intercompany balances."""

    entity_id: str
    entity_name: str
    trial_balance: Dict[str, float]  # account_code -> balance_eur
    intercompany_receivables: Dict[str, float]  # counterparty_entity_id -> amount_eur (Account 411)
    intercompany_payables: Dict[str, float]  # counterparty_entity_id -> amount_eur (Account 401)


@dataclasses.dataclass
class ConsolidatedFinancialStatement:
    """Dataclass holding consolidated group financial statement."""

    group_name: str
    consolidated_balance_sheet: Dict[str, float]
    eliminated_intercompany_amount_eur: float
    elimination_entries: List[Dict[str, Any]]


class CorporateConsolidationEngine:
    """Engine orchestrating multi-entity corporate consolidation and intercompany eliminations."""

    @classmethod
    def consolidate_group_financials(
        cls, group_name: str, entities: List[EntityFinancialTrialBalance]
    ) -> ConsolidatedFinancialStatement:
        """Consolidates trial balances across entities and eliminates intercompany balances."""
        consolidated_accounts: Dict[str, float] = {}
        elimination_entries: List[Dict[str, Any]] = []
        total_eliminated = 0.0

        # Step 1: Aggregate trial balances
        for entity in entities:
            for acc, bal in entity.trial_balance.items():
                consolidated_accounts[acc] = round(consolidated_accounts.get(acc, 0.0) + bal, 2)

        # Step 2: Detect & Eliminate Intercompany 411 / 401 balances
        entity_map = {e.entity_id: e for e in entities}

        for e_id, entity in entity_map.items():
            for target_id, rec_amt in entity.intercompany_receivables.items():
                if target_id in entity_map:
                    target_entity = entity_map[target_id]
                    pay_amt = target_entity.intercompany_payables.get(e_id, 0.0)

                    elim_amt = min(rec_amt, pay_amt)
                    if elim_amt > 0:
                        total_eliminated += elim_amt
                        # Deduct from consolidated 411 and 401
                        consolidated_accounts["411"] = round(consolidated_accounts.get("411", 0.0) - elim_amt, 2)
                        consolidated_accounts["401"] = round(consolidated_accounts.get("401", 0.0) - elim_amt, 2)

                        elimination_entries.append(
                            {
                                "document_number": f"ELIM_{e_id}_{target_id}",
                                "debit_account": "401",  # Payables / Доставчици
                                "credit_account": "411",  # Receivables / Клиенти
                                "amount_eur": round(elim_amt, 2),
                                "narrative": f"Консолидационно елиминиране на вътрешногрупови разчети ({entity.entity_name} ↔ {target_entity.entity_name})",
                            }
                        )

        total_eliminated = round(total_eliminated, 2)
        statement = ConsolidatedFinancialStatement(
            group_name=group_name,
            consolidated_balance_sheet=consolidated_accounts,
            eliminated_intercompany_amount_eur=total_eliminated,
            elimination_entries=elimination_entries,
        )

        logger.info(
            f"🏛️ Corporate Consolidation [{group_name}]: {len(entities)} entities consolidated, "
            f"€{total_eliminated:,.2f} intercompany balances eliminated."
        )
        return statement
