"""
Unit tests for Open Banking PSD2 / Berlin Group REST API Stream Ingestion Engine.
"""

import unittest

from src.intake.psd2_openbanking import PSD2BankProvider, PSD2OpenBankingClient


class TestPSD2OpenBanking(unittest.TestCase):
    """Test suite for PSD2OpenBankingClient."""

    def test_consent_token_retrieval(self):
        token = PSD2OpenBankingClient.get_consent_token(PSD2BankProvider.DSK)
        self.assertTrue(token.startswith("psd2_token_dsk_"))

    def test_fetch_transactions_stream_dsk(self):
        txs = PSD2OpenBankingClient.fetch_transactions_stream(
            bank=PSD2BankProvider.DSK,
            iban="BG71STSA93000028013479",
            date_from="2026-01-01",
            date_to="2026-01-31",
        )
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0]["source"], "PSD2_STREAM_DSK")
        self.assertIn("debit_amount", txs[0])

    def test_fetch_transactions_stream_unicredit(self):
        txs = PSD2OpenBankingClient.fetch_transactions_stream(
            bank=PSD2BankProvider.UNICREDIT,
            iban="BG18UNCR96601012345678",
            date_from="2026-01-01",
            date_to="2026-01-31",
        )
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0]["source"], "PSD2_STREAM_UNICREDIT")


if __name__ == "__main__":
    unittest.main()
