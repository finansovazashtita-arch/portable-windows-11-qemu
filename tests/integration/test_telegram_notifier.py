"""
Unit tests for Mobile Notifications & Telegram Bot Guard Module.
"""

import unittest
from src.integration.telegram_notifier import TelegramNotifier


class TestTelegramNotifier(unittest.TestCase):
    """Test suite for TelegramNotifier."""

    def test_send_alert_offline_fallback(self):
        res = TelegramNotifier.send_alert("Тестово съобщение за одит системата.")
        self.assertTrue(res)

    def test_send_fraud_alert_formatting(self):
        tx = {
            "counterparty_name": "ИЗМАМА ООД",
            "debit_amount": 15000.0,
            "document_number": "INV_99999",
        }
        res = TelegramNotifier.send_fraud_alert(
            risk_level="CRITICAL",
            risk_score=0.95,
            flags=["UNVERIFIED_IBAN", "SUSPICIOUS_KEYWORD"],
            tx=tx,
        )
        self.assertTrue(res)

    def test_send_cluster_alert_formatting(self):
        res = TelegramNotifier.send_cluster_alert(
            event="FAILOVER_EXECUTED",
            leader_node="macmini-secondary",
            leader_host="100.70.181.127",
        )
        self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
