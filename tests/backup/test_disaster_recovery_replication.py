"""
Unit tests for Continuous Disaster Recovery (DR) Multi-Region Replication Engine.
"""

import os
import tempfile
import unittest

from src.backup.disaster_recovery_replication import DRReplicationManager, ReplicationTarget


class TestDRReplicationManager(unittest.TestCase):
    """Test suite for DRReplicationManager."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dr_mgr = DRReplicationManager(backup_dir=self.temp_dir.name)

        # Create sample backup payload file
        self.sample_payload = os.path.join(self.temp_dir.name, "sqlexpress_backup_test.bak")
        with open(self.sample_payload, "w", encoding="utf-8") as f:
            f.write("SQL_SERVER_SAMPLE_DATABASE_BACKUP_DUMP_CONTENT")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sha256_hash_computation(self):
        h = self.dr_mgr.compute_sha256(self.sample_payload)
        self.assertTrue(len(h) == 64)

    def test_replicate_payload_success(self):
        res = self.dr_mgr.replicate_payload(self.sample_payload, ReplicationTarget.SECONDARY_STANDBY)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["target"], "macmini-secondary")

        # Verify replica existence
        replica_file = os.path.join(self.temp_dir.name, "dr_replicas", "macmini-secondary", "sqlexpress_backup_test.bak")
        self.assertTrue(os.path.exists(replica_file))

    def test_run_full_dr_sync(self):
        res = self.dr_mgr.run_full_dr_sync()
        self.assertEqual(res["dr_status"], "COMPLETED")
        self.assertGreater(res["replications_count"], 0)


if __name__ == "__main__":
    unittest.main()
