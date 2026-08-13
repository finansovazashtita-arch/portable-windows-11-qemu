"""
Unit tests for Automated Financial Audit Trail & Tamper-Evident Blockchain Ledger Integration (Audit Ledger Integrity Guard).
"""

import unittest

from src.security.audit_ledger_guard import AuditLedgerIntegrityGuard


class TestAuditLedgerIntegrityGuard(unittest.TestCase):
    """Test suite for AuditLedgerIntegrityGuard."""

    def test_append_entries_and_verify_valid_chain(self):
        guard = AuditLedgerIntegrityGuard()

        guard.append_entry({"doc": "INV-101", "amount_eur": 1000.0}, timestamp_str="2026-06-15T10:00:00Z")
        guard.append_entry({"doc": "PAY-102", "amount_eur": 1000.0}, timestamp_str="2026-06-15T10:05:00Z")

        is_valid, err = guard.verify_chain_integrity()
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        summary = guard.export_chain_summary()
        self.assertEqual(summary["total_blocks"], 3)  # Genesis + 2 entries
        self.assertTrue(summary["chain_valid"])

    def test_tamper_detection_fails_verification(self):
        guard = AuditLedgerIntegrityGuard()

        guard.append_entry({"doc": "INV-201", "amount_eur": 500.0}, timestamp_str="2026-06-15T11:00:00Z")
        guard.append_entry({"doc": "INV-202", "amount_eur": 800.0}, timestamp_str="2026-06-15T11:10:00Z")

        # Tamper with block #1 data
        guard.chain[1].entry_data["amount_eur"] = 9999.0

        is_valid, err = guard.verify_chain_integrity()
        self.assertFalse(is_valid)
        self.assertIn("Block data tampered at block #1", err)


if __name__ == "__main__":
    unittest.main()
