"""
Unit tests for Zero-Trust DR Failover & Instant Recovery Orchestrator Engine (M59).
"""

import time
import unittest

from src.cluster.dr_failover_orchestrator import (
    DBSyncVerification,
    DRState,
    FailoverExecutionReport,
    FailoverMode,
    NodeHealthProbe,
    ProbeStatus,
    VMSyncState,
    ZeroTrustDROrchestrator,
)
from src.cluster.ha_failover import NodeRole, NodeStatus


class TestZeroTrustDROrchestrator(unittest.TestCase):
    """Test suite for ZeroTrustDROrchestrator."""

    def setUp(self):
        self.orchestrator = ZeroTrustDROrchestrator(
            primary_node_id="macmini-primary",
            secondary_node_id="macmini-secondary",
            target_rto_seconds=5.0,
            zero_trust_secret="Test-DR-Secret-12345",
        )

    def test_initial_dr_orchestration_status(self):
        status = self.orchestrator.get_dr_orchestration_status()
        self.assertEqual(status["orchestrator_state"], DRState.HEALTHY_PRIMARY.value)
        self.assertEqual(status["primary_node_id"], "macmini-primary")
        self.assertEqual(status["secondary_node_id"], "macmini-secondary")
        self.assertEqual(status["active_leader_id"], "macmini-primary")
        self.assertEqual(status["target_rto_seconds"], 5.0)
        self.assertIsNone(status["last_drill_timestamp"])

    def test_zero_trust_token_generation_and_validation(self):
        token = self.orchestrator.generate_zero_trust_token()
        self.assertTrue(self.orchestrator.verify_zero_trust_token(token))

        # Invalid token signature
        invalid_token = token.replace("a", "b") if "a" in token else token + "x"
        self.assertFalse(self.orchestrator.verify_zero_trust_token(invalid_token))

        # Expired token
        old_timestamp = time.time() - 400
        expired_token = self.orchestrator.generate_zero_trust_token(timestamp=old_timestamp)
        self.assertFalse(self.orchestrator.verify_zero_trust_token(expired_token))

    def test_execute_health_probes(self):
        probes = self.orchestrator.execute_health_probes()
        self.assertIn("macmini-primary", probes)
        self.assertIn("macmini-secondary", probes)
        self.assertIsInstance(probes["macmini-primary"], NodeHealthProbe)
        self.assertIn(probes["macmini-primary"].status, [ProbeStatus.PASSED, ProbeStatus.DEGRADED])

    def test_verify_vm_state_cloning(self):
        vm_state = self.orchestrator.verify_vm_state_cloning("win11-deltapro-vm")
        self.assertIsInstance(vm_state, VMSyncState)
        self.assertEqual(vm_state.vm_id, "win11-deltapro-vm")
        self.assertTrue(vm_state.qcow2_cloned)
        self.assertTrue(vm_state.ram_state_synced)
        self.assertEqual(vm_state.sync_status, "SYNCED")

    def test_verify_database_sync(self):
        db_sync = self.orchestrator.verify_database_sync()
        self.assertIsInstance(db_sync, DBSyncVerification)
        self.assertTrue(db_sync.is_rpo_zero)
        self.assertEqual(db_sync.pending_mutations_count, 0)

    def test_execute_failover_drill_success(self):
        report = self.orchestrator.execute_failover_drill()
        self.assertIsInstance(report, FailoverExecutionReport)
        self.assertEqual(report.status, DRState.FAILOVER_COMPLETED)
        self.assertEqual(report.mode, FailoverMode.SCHEDULED_DRILL)
        self.assertTrue(report.zero_trust_verified)
        self.assertTrue(report.target_rto_met)
        self.assertLessEqual(report.rto_seconds, 5.0)
        self.assertEqual(report.promoted_leader_id, "macmini-secondary")
        self.assertEqual(self.orchestrator.ha_manager.active_leader_id, "macmini-secondary")

        # Verify status summary updated
        status = self.orchestrator.get_dr_orchestration_status()
        self.assertEqual(status["active_leader_id"], "macmini-secondary")
        self.assertEqual(status["drills_count"], 1)

    def test_execute_failover_drill_forced_failure(self):
        report = self.orchestrator.execute_failover_drill(force_failure=True)
        self.assertEqual(report.status, DRState.FAILOVER_FAILED)
        self.assertEqual(report.trigger_reason, "SIMULATED_FAILURE")

    def test_trigger_emergency_failover(self):
        report = self.orchestrator.trigger_emergency_failover("macmini-primary")
        self.assertEqual(report.status, DRState.FAILOVER_COMPLETED)
        self.assertEqual(report.mode, FailoverMode.AUTOMATIC_DISASTER)
        self.assertEqual(report.promoted_leader_id, "macmini-secondary")
        self.assertTrue(report.target_rto_met)


if __name__ == "__main__":
    unittest.main()
