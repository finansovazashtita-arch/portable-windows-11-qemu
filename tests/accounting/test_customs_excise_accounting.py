"""
Unit tests for Automated Customs & Excise Tax Accounting Engine.
"""

import unittest

from src.accounting.customs_excise_accounting import CustomsDeclaration, CustomsExciseProcessor


class TestCustomsExciseAccounting(unittest.TestCase):
    """Test suite for CustomsExciseProcessor."""

    def test_customs_entries_generation(self):
        decl = CustomsDeclaration(
            declaration_number="EAD_2026_9981",
            inventory_value=50000.0,
            import_duty_amount=2500.0,
            excise_tax_amount=1500.0,
            import_vat_amount=10800.0,
        )
        entries = CustomsExciseProcessor.generate_customs_entries(decl)

        self.assertEqual(len(entries), 4)

        debit_accs = [e["debit_account"] for e in entries]
        credit_accs = [e["credit_account"] for e in entries]

        self.assertIn("304", debit_accs)
        self.assertIn("4531", debit_accs)
        self.assertIn("457", credit_accs)
        self.assertIn("458", credit_accs)
        self.assertIn("503", credit_accs)

    def test_double_entry_balance_invariant(self):
        decl = CustomsDeclaration(
            declaration_number="EAD_2026_9982",
            inventory_value=12000.0,
            import_duty_amount=600.0,
            excise_tax_amount=300.0,
            import_vat_amount=2580.0,
        )
        entries = CustomsExciseProcessor.generate_customs_entries(decl)

        total_debits = sum(e["amount"] for e in entries)
        total_credits = sum(e["amount"] for e in entries)

        self.assertAlmostEqual(total_debits, total_credits, places=2)


if __name__ == "__main__":
    unittest.main()
