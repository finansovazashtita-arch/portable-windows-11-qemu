"""
Unit tests for Obsidian Vault Exporter.
"""

import json
import os
import tempfile
import unittest

from src.integration.obsidian_exporter import ObsidianVaultExporter


class TestObsidianVaultExporter(unittest.TestCase):
    """Test suite for ObsidianVaultExporter."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.exporter = ObsidianVaultExporter(
            vault_path=self.temp_dir.name,
            subfolder="Test-Accounting"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_statement_note(self):
        json_path = os.path.join(self.temp_dir.name, "extracted.json")
        journal_path = os.path.join(self.temp_dir.name, "journal.json")
        audit_path = os.path.join(self.temp_dir.name, "TRANSFER.LOG")

        sample_extracted = {
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
                {"debit_amount": 100.00, "credit_amount": 0.00},
                {"debit_amount": 0.00, "credit_amount": 50.00}
            ]
        }

        sample_journal = {
            "journal_entries": [
                {
                    "posting_date": "2026-01-05",
                    "document_number": "1001",
                    "narrative_description": "Плащане фактура наем",
                    "debit_account": "602",
                    "credit_account": "503",
                    "amount": 100.00
                }
            ]
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(sample_extracted, f)

        with open(journal_path, "w", encoding="utf-8") as f:
            json.dump(sample_journal, f)

        with open(audit_path, "w", encoding="utf-8") as f:
            f.write("TRANSFER_LOG_OK")

        note_path = self.exporter.export_statement_note(json_path, journal_path, audit_path)
        self.assertIsNotNone(note_path)
        self.assertTrue(os.path.exists(note_path))

        with open(note_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("СТОРГОЗИЯ АД", content)
        self.assertIn("114077876", content)
        self.assertIn("BG71STSA93000028013479", content)
        self.assertIn("503", content)
        self.assertIn("602", content)
        self.assertIn("RECONCILED_0.00_EUR", content)


if __name__ == "__main__":
    unittest.main()
