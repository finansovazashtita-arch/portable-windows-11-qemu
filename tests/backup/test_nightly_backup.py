"""
Unit tests for Automated Nightly Backup Manager Module.
"""

import os
import tempfile
import time
import unittest

from src.backup.nightly_backup import NightlyBackupManager


class TestNightlyBackupManager(unittest.TestCase):
    """Test suite for NightlyBackupManager."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.backup_mgr = NightlyBackupManager(backup_root_dir=self.temp_dir.name, retention_days=30)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_backup_mssql_database(self):
        ok, path = self.backup_mgr.backup_mssql_database("DeltaProTest")
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(path))
        self.assertIn("DeltaProTest_snapshot_", path)

    def test_backup_transfer_log(self):
        sample_log = os.path.join(self.temp_dir.name, "sample_TRANSFER.LOG")
        with open(sample_log, "w", encoding="utf-8") as f:
            f.write("TRANSFER_LOG_CONTENT_TEST")

        ok, path = self.backup_mgr.backup_transfer_log(sample_log)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(path))

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "TRANSFER_LOG_CONTENT_TEST")

    def test_backup_infisical_secrets(self):
        ok, path = self.backup_mgr.backup_infisical_secrets()
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(path))

    def test_run_full_nightly_backup(self):
        summary = self.backup_mgr.run_full_nightly_backup()
        self.assertEqual(summary.overall_status, "SUCCESS")
        self.assertEqual(summary.mssql_backup_status, "SUCCESS")
        self.assertEqual(summary.transfer_log_status, "SUCCESS")
        self.assertEqual(summary.infisical_backup_status, "SUCCESS")


if __name__ == "__main__":
    unittest.main()
