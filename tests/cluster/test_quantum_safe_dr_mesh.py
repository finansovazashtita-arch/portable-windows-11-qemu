"""
Unit tests for Quantum-Safe Active-Active DR Mesh Orchestrator (M63).
"""

import time
import unittest

from src.cluster.dr_failover_orchestrator import DRState, FailoverMode
from src.cluster.quantum_safe_dr_mesh import (
    CloudProvider,
    K3sClusterNode,
    MeshFailoverEvent,
    MeshHealthConsensus,
    MeshNodeState,
    MeshTopology,
    QuantumSafeDRMesh,
    SplitBrainStrategy,
    WireGuardTunnel,
)


class TestQuantumSafeDRMesh(unittest.TestCase):
    """Test suite for QuantumSafeDRMesh."""

    def setUp(self):
        self.mesh = QuantumSafeDRMesh()

    def test_default_mesh_initialization(self):
        self.assertEqual(len(self.mesh.mesh_nodes), 3)
        providers = [node.cloud_provider for node in self.mesh.mesh_nodes.values()]
        self.assertIn(CloudProvider.AWS, providers)
        self.assertIn(CloudProvider.HETZNER, providers)
        self.assertIn(CloudProvider.ONPREM, providers)

    def test_mesh_node_properties(self):
        for node in self.mesh.mesh_nodes.values():
            self.assertTrue(hasattr(node, "cloud_provider"))
            self.assertTrue(hasattr(node, "region"))
            self.assertTrue(hasattr(node, "api_server_url"))
            self.assertEqual(node.state, MeshNodeState.ACTIVE)

    def test_wireguard_tunnels_established(self):
        # 3 nodes in FULL_MESH -> 3 WireGuard tunnels
        self.assertEqual(len(self.mesh.wireguard_tunnels), 3)
        for tunnel in self.mesh.wireguard_tunnels.values():
            self.assertIsInstance(tunnel, WireGuardTunnel)
            self.assertTrue(tunnel.is_active)

    def test_register_additional_node(self):
        node = self.mesh.register_mesh_node(
            node_id="aws-eu-west-1",
            cloud_provider=CloudProvider.AWS,
            region="eu-west-1",
            api_server_url="https://k3s-aws2.finansprotect.eu:6443",
        )
        self.assertIsInstance(node, K3sClusterNode)
        self.assertEqual(len(self.mesh.mesh_nodes), 4)
        self.assertIn("aws-eu-west-1", self.mesh.mesh_nodes)

    def test_establish_wireguard_tunnel(self):
        self.mesh.register_mesh_node(
            node_id="aws-eu-west-1",
            cloud_provider=CloudProvider.AWS,
            region="eu-west-1",
        )
        tunnel = self.mesh.establish_wireguard_tunnel("aws-eu-central-1", "aws-eu-west-1")
        self.assertIsInstance(tunnel, WireGuardTunnel)
        self.assertEqual(tunnel.node_a, "aws-eu-central-1")
        self.assertEqual(tunnel.node_b, "aws-eu-west-1")

    def test_execute_mesh_health_consensus(self):
        consensus = self.mesh.execute_mesh_health_consensus()
        self.assertIsInstance(consensus, MeshHealthConsensus)
        self.assertTrue(consensus.quorum_reached)
        self.assertEqual(len(consensus.healthy_nodes), 3)
        self.assertIsNotNone(consensus.consensus_hash)

    def test_detect_split_brain_no_partition(self):
        partitions = self.mesh.detect_split_brain()
        self.assertIn("group_a", partitions)
        self.assertEqual(len(partitions["group_b"]), 0)

    def test_detect_split_brain_with_failure(self):
        node_id = list(self.mesh.mesh_nodes.keys())[0]
        self.mesh.mesh_nodes[node_id].state = MeshNodeState.PARTITIONED
        partitions = self.mesh.detect_split_brain()
        self.assertIn(node_id, partitions["group_b"])

    def test_resolve_split_brain_quorum(self):
        partitions = {
            "group_a": ["aws-eu-central-1", "hetzner-fsn1"],
            "group_b": ["onprem-macmini"],
        }
        winning_leader = self.mesh.resolve_split_brain(partitions)
        self.assertEqual(winning_leader, "aws-eu-central-1")

    def test_execute_mesh_failover(self):
        failed_node_id = "aws-eu-central-1"
        event = self.mesh.execute_mesh_failover(failed_node_id=failed_node_id, reason="NODE_FAILURE")
        self.assertIsInstance(event, MeshFailoverEvent)
        self.assertEqual(event.failed_node_id, failed_node_id)
        self.assertTrue(event.pqc_verified)
        self.assertLess(event.rto_seconds, self.mesh.target_rto_seconds)
        self.assertEqual(self.mesh.mesh_nodes[failed_node_id].state, MeshNodeState.FAILED)

    def test_execute_cross_region_dr_drill(self):
        report = self.mesh.execute_cross_region_dr_drill()
        self.assertIsInstance(report, dict)
        self.assertEqual(report["overall_status"], "SUCCESS")
        self.assertIn("results", report)
        self.assertEqual(len(report["results"]), 3)

    def test_rotate_mesh_certificates(self):
        result = self.mesh.rotate_mesh_certificates()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["rotated_certificates"], 3)

    def test_get_mesh_topology_status(self):
        status = self.mesh.get_mesh_topology_status()
        self.assertIsInstance(status, dict)
        self.assertEqual(status["mesh_id"], "finansprotect-dr-mesh")
        self.assertEqual(status["topology"], "FULL_MESH")
        self.assertIn("nodes", status)
        self.assertIn("tunnels", status)
        self.assertEqual(status["healthy_node_count"], 3)


if __name__ == "__main__":
    unittest.main()
