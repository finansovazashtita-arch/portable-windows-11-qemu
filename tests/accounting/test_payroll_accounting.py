"""
Unit tests for Automated Payroll & Social Security Ledger Integration Engine.
"""

import unittest

from src.accounting.payroll_accounting import PayrollProcessor, PayrollSummary


class TestPayrollAccounting(unittest.TestCase):
    """Test suite for PayrollProcessor and PayrollSummary."""

    def test_payroll_summary_net_calculation(self):
        payroll = PayrollSummary(
            gross_salaries=10000.0,
            employee_social_security=1378.0,
            employee_income_tax=862.20,
            employer_social_security=1892.0,
        )
        self.assertEqual(payroll.net_salaries, 7759.80)
        self.assertEqual(payroll.total_cost_for_company, 11892.0)

    def test_generate_payroll_entries_count_and_balance(self):
        payroll = PayrollSummary(
            gross_salaries=5000.0,
            employee_social_security=689.0,
            employee_income_tax=431.10,
            employer_social_security=946.0,
        )
        entries = PayrollProcessor.generate_payroll_entries(payroll)

        self.assertEqual(len(entries), 5)

        # Verify Accounts
        debit_accounts = [e["debit_account"] for e in entries]
        credit_accounts = [e["credit_account"] for e in entries]

        self.assertIn("604", debit_accounts)
        self.assertIn("421", debit_accounts)
        self.assertIn("605", debit_accounts)
        self.assertIn("455", credit_accounts)
        self.assertIn("454", credit_accounts)
        self.assertIn("503", credit_accounts)

    def test_double_entry_balance_invariant(self):
        payroll = PayrollSummary(
            gross_salaries=2000.0,
            employee_social_security=275.60,
            employee_income_tax=172.44,
            employer_social_security=378.40,
        )
        entries = PayrollProcessor.generate_payroll_entries(payroll)

        total_debits = sum(e["amount"] for e in entries)
        total_credits = sum(e["amount"] for e in entries)

        self.assertAlmostEqual(total_debits, total_credits, places=2)


if __name__ == "__main__":
    unittest.main()
