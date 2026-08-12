"""
Unit tests for Supabase Logger.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.integration.supabase_logger import SupabaseLogger


class TestSupabaseLogger(unittest.TestCase):
    """Test suite for SupabaseLogger."""

    def setUp(self):
        self.logger_client = SupabaseLogger(
            base_url="http://127.0.0.1:8002",
            service_key="test_key",
            timeout=2
        )

    @patch("urllib.request.urlopen")
    def test_log_statement_run_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        sample_data = {
            "statement_metadata": {
                "account_holder": "СТОРГОЗИЯ АД",
                "eik": "114077876",
                "iban": "BG71STSA93000028013479",
                "currency": "EUR",
                "period_start": "01.01.2026",
                "period_end": "31.01.2026",
                "opening_balance": 5883.29
            },
            "transactions": [
                {"debit_amount": 100.00, "credit_amount": 0.00}
            ]
        }

        res = self.logger_client.log_statement_run(sample_data, status="SUCCESS", audit_sha256="sha256test")
        self.assertTrue(res)

    def test_log_statement_run_offline_fallback(self):
        sample_data = {
            "statement_metadata": {"account_holder": "TEST"},
            "transactions": []
        }
        res = self.logger_client.log_statement_run(sample_data, status="ERROR")
        self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
