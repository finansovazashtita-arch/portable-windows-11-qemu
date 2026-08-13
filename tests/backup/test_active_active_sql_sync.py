"""
Unit tests for Multi-Region Active-Active SQL Database Synchronization Guard Engine (RPO=0).
"""

import unittest

from src.backup.active_active_sql_sync import ActiveActiveSQLSyncGuard, DatabaseType, SyncStatus


class TestActiveActiveSQLSyncGuard(unittest.TestCase):
    """Test suite for ActiveActiveSQLSyncGuard."""

    def setUp(self):
        self.guard = ActiveActiveSQLSyncGuard()

    def test_replicate_mutation(self):
        payload = self.guard.replicate_mutation("Operations", 21, db_type=DatabaseType.MS_SQL_SERVER)

        self.assertEqual(payload.table_name, "Operations")
        self.assertEqual(payload.rows_affected, 21)
        self.assertEqual(payload.db_type, DatabaseType.MS_SQL_SERVER)
        self.assertEqual(len(payload.sha256_state_hash), 64)

    def test_resolve_sync_conflict_exact_match(self):
        p1 = self.guard.replicate_mutation("Partners", 5, db_type=DatabaseType.POSTGRESQL)
        status = self.guard.resolve_sync_conflict(p1, p1)
        self.assertEqual(status, SyncStatus.IN_SYNC)

    def test_get_cluster_sync_state(self):
        self.guard.replicate_mutation("OperationDetails", 42)
        state = self.guard.get_cluster_sync_state()

        self.assertEqual(state["rpo_objective_seconds"], 0)
        self.assertEqual(state["status"], "IN_SYNC")
        self.assertEqual(state["replicated_mutations_count"], 1)


if __name__ == "__main__":
    unittest.main()
