"""
Unit tests for Autonomous Open Banking Payment Initiation & Multi-Bank AISP Aggregator (PISP / AISP Adapter).
"""

import unittest

from src.intake.open_banking_pisp import OpenBankingPISPAggregator, PaymentInitiationRequest


class TestOpenBankingPISPAggregator(unittest.TestCase):
    """Test suite for OpenBankingPISPAggregator."""

    def test_initiate_vendor_payment_dsk(self):
        req = PaymentInitiationRequest(
            payment_id="PMT-501",
            debtor_iban="BG71STSA93000028013479",
            creditor_iban="BG12UNCR70001524896321",
            creditor_name="ТехноЛоджикс ЕООД",
            amount_eur=1450.0,
            remittance_info="Фактура 100025",
            bank_code="DSK",
        )

        res = OpenBankingPISPAggregator.initiate_vendor_payment(req)

        self.assertEqual(res.transaction_status, "ACCP")
        self.assertTrue(res.psd2_consent_id.startswith("CONSENT_PSD2_"))
        self.assertEqual(res.journal_entry["debit_account"], "401")
        self.assertEqual(res.journal_entry["credit_account"], "503")
        self.assertEqual(res.journal_entry["amount_eur"], 1450.0)

    def test_aggregate_multi_bank_balances(self):
        ibans = {
            "DSK": "BG71STSA93000028013479",
            "UNCR": "BG12UNCR70001524896321",
        }

        agg = OpenBankingPISPAggregator.aggregate_multi_bank_balances(ibans)

        self.assertEqual(agg["bank_count"], 2)
        self.assertEqual(agg["total_consolidated_balance_eur"], 40000.0)


if __name__ == "__main__":
    unittest.main()
