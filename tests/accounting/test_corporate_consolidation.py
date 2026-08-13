"""
Unit tests for Autonomous Multi-Entity Corporate Consolidation & Intercompany Elimination Engine.
"""

import unittest

from src.accounting.corporate_consolidation import CorporateConsolidationEngine, EntityFinancialTrialBalance


class TestCorporateConsolidationEngine(unittest.TestCase):
    """Test suite for CorporateConsolidationEngine."""

    def test_consolidate_group_financials_with_elimination(self):
        # Parent company
        parent = EntityFinancialTrialBalance(
            entity_id="HOLDING_CO",
            entity_name="Булгариа Холдинг АД",
            trial_balance={"503": 100000.0, "411": 25000.0, "702": 150000.0},
            intercompany_receivables={"SUB_1": 25000.0},  # Intercompany loan/sale to SUB_1
            intercompany_payables={},
        )

        # Subsidiary 1
        sub1 = EntityFinancialTrialBalance(
            entity_id="SUB_1",
            entity_name="Сторгозия Трейд ЕООД",
            trial_balance={"503": 50000.0, "401": 25000.0, "702": 80000.0},
            intercompany_receivables={},
            intercompany_payables={"HOLDING_CO": 25000.0},  # Intercompany payable to HOLDING_CO
        )

        statement = CorporateConsolidationEngine.consolidate_group_financials(
            group_name="Булгариа Груп Холдинг",
            entities=[parent, sub1],
        )

        self.assertEqual(statement.group_name, "Булгариа Груп Холдинг")
        self.assertEqual(statement.eliminated_intercompany_amount_eur, 25000.0)
        self.assertEqual(len(statement.elimination_entries), 1)

        # Consolidated balance sheet: Accounts 411 and 401 should be 0.0 after elimination
        self.assertEqual(statement.consolidated_balance_sheet.get("411"), 0.0)
        self.assertEqual(statement.consolidated_balance_sheet.get("401"), 0.0)
        self.assertEqual(statement.consolidated_balance_sheet.get("503"), 150000.0)
        self.assertEqual(statement.consolidated_balance_sheet.get("702"), 230000.0)


if __name__ == "__main__":
    unittest.main()
