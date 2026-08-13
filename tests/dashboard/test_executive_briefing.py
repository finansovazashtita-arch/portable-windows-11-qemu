"""
Unit tests for Multi-Language Executive Financial Briefing Generator Engine.
"""

import unittest

from src.dashboard.executive_briefing import BriefingLanguage, ExecutiveBriefingGenerator


class TestExecutiveBriefingGenerator(unittest.TestCase):
    """Test suite for ExecutiveBriefingGenerator."""

    def test_generate_briefing_bulgarian(self):
        report = ExecutiveBriefingGenerator.generate_briefing(
            daily_turnover_eur=12500.50,
            transaction_count=42,
            language=BriefingLanguage.BULGARIAN,
        )

        self.assertEqual(report.language, BriefingLanguage.BULGARIAN)
        self.assertIn("12,500.50 EUR", report.daily_turnover_formatted)
        self.assertIn("Ежедневен Финансов Доклад", report.title)
        self.assertEqual(report.total_transactions_count, 42)

    def test_generate_briefing_english(self):
        report = ExecutiveBriefingGenerator.generate_briefing(
            daily_turnover_eur=50000.00,
            transaction_count=100,
            language=BriefingLanguage.ENGLISH,
        )

        self.assertEqual(report.language, BriefingLanguage.ENGLISH)
        self.assertIn("Daily Executive Financial Briefing", report.title)

    def test_generate_briefing_german(self):
        report = ExecutiveBriefingGenerator.generate_briefing(
            daily_turnover_eur=50000.00,
            transaction_count=100,
            language=BriefingLanguage.GERMAN,
        )

        self.assertEqual(report.language, BriefingLanguage.GERMAN)
        self.assertIn("Tägliche Finanzzusammenfassung", report.title)


if __name__ == "__main__":
    unittest.main()
