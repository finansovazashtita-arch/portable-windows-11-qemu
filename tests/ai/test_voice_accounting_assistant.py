"""
Unit tests for Intelligent AI Voice Assistant & Hands-Free Accounting Query Interface.
"""

import unittest

from src.ai.voice_accounting_assistant import VoiceAccountingAssistant, VoiceQueryType


class TestVoiceAccountingAssistant(unittest.TestCase):
    """Test suite for VoiceAccountingAssistant."""

    def test_turnover_voice_query(self):
        res = VoiceAccountingAssistant.process_voice_query("Какъв е оборотът за днес?", {"turnover_eur": 1000.0})
        self.assertEqual(res.query_type, VoiceQueryType.TURNOVER_QUERY)
        self.assertIn("1,000.00 евро", res.spoken_response_bg)

    def test_balance_voice_query(self):
        res = VoiceAccountingAssistant.process_voice_query("Колко е салдото по сметката?", {"balance_bgn": 25000.0})
        self.assertEqual(res.query_type, VoiceQueryType.BALANCE_QUERY)
        self.assertIn("25,000.00 лева", res.spoken_response_bg)

    def test_missing_invoices_voice_query(self):
        res = VoiceAccountingAssistant.process_voice_query("Има ли липсващи фактури?")
        self.assertEqual(res.query_type, VoiceQueryType.MISSING_INVOICES)
        self.assertIn("Няма липсващи фактури", res.spoken_response_bg)


if __name__ == "__main__":
    unittest.main()
