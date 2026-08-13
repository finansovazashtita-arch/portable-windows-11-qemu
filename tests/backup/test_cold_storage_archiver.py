"""
Unit tests for Autonomous Audit Log Cold Storage Archiving Engine (10-Year NRA Compliance).
"""

import os
import tempfile
import unittest

from src.backup.cold_storage_archiver import ArchiveFormat, AuditLogColdArchiver, ColdStorageArchive


class TestAuditLogColdArchiver(unittest.TestCase):
    """Test suite for AuditLogColdArchiver."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.archiver = AuditLogColdArchiver(cold_archive_dir=self.temp_dir.name)

        # Create sample log file
        self.sample_log = os.path.join(self.temp_dir.name, "TRANSFER.LOG")
        with open(self.sample_log, "w", encoding="utf-8") as f:
            f.write("TRANSFER_LOG_AUDIT_TRAIL_SAMPLE_DATA_FOR_NRA_10_YEAR_RETENTION\n" * 50)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_cold_archive_success(self):
        archive = self.archiver.create_cold_archive(self.sample_log)

        self.assertTrue(os.path.exists(archive.file_path))
        self.assertEqual(archive.retention_years, 10)
        self.assertLess(archive.compressed_bytes, archive.uncompressed_bytes)

    def test_restore_cold_archive_success(self):
        archive = self.archiver.create_cold_archive(self.sample_log)
        restore_dir = os.path.join(self.temp_dir.name, "restored")

        restored_file = self.archiver.restore_cold_archive(archive, restore_dir)
        self.assertTrue(os.path.exists(restored_file))

        with open(restored_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("TRANSFER_LOG_AUDIT_TRAIL_SAMPLE_DATA", content)

    def test_create_eidas_compliance_vault_archive(self):
        vault_path = self.archiver.create_eidas_compliance_vault_archive(
            self.sample_log, nra_tax_code="TEST-NRA-VAULT"
        )
        self.assertTrue(os.path.exists(vault_path))
        self.assertGreater(os.path.getsize(vault_path), 500)


if __name__ == "__main__":
    unittest.main()

