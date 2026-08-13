import time
import unittest
from datetime import datetime

from src.cluster.quantum_safe_dr_mesh import (
    QuantumSafeDRMesh, CloudProvider, MeshNodeState, MeshTopology,
    SplitBrainStrategy, K3sClusterNode, MeshHealthConsensus,
    WireGuardTunnel, MeshFailoverEvent,
)
from src.cluster.dr_failover_orchestrator import DRState, FailoverMode

class TestQuantumSafeDRMesh(unittest.TestCase):
    def setUp(self):
        self.mesh = QuantumSafeDRMesh()

    def test_default_mesh_initialization(self):
        self.assertEqual(len(self.mesh.nodes), 3)
        providers = [node.cloud_provider for node in self.mesh.nodes.values()]
        self.assertIn(CloudProvider.AWS, providers)
        self.assertIn(CloudProvider.HETZNER, providers)
        self.assertIn(CloudProvider.ONPREM, providers)

    def test_mesh_node_properties(self):
        for node in self.mesh.nodes.values():
            self.assertTrue(hasattr(node, 'cloud_provider'))
            self.assertTrue(hasattr(node, 'region'))
            self.assertTrue(hasattr(node, 'api_server_url'))

    def test_wireguard_tunnels_established(self):
        self.assertEqual(len(self.mesh.tunnels), 3)
        # Should exist between all pairs in a 3-node mesh
        endpoints = set()
        for tunnel in self.mesh.tunnels:
            endpoints.add(f"{tunnel.endpoint1}-{tunnel.endpoint2}")
            endpoints.add(f"{tunnel.endpoint2}-{tunnel.endpoint1}")
        self.assertTrue(len(endpoints) >= 3)

    def test_register_additional_node(self):
        new_node = K3sClusterNode(
            node_id="node_4",
            cloud_provider=CloudProvider.AWS,
            region="us-east-1",
            api_server_url="https://node_4",
            state=MeshNodeState.HEALTHY
        )
        self.mesh.register_node(new_node)
        self.assertEqual(len(self.mesh.nodes), 4)
        self.assertIn("node_4", self.mesh.nodes)

    def test_establish_wireguard_tunnel(self):
        tunnel = self.mesh.establish_wireguard_tunnel("node_aws", "node_4")
        self.assertIsInstance(tunnel, WireGuardTunnel)
        self.assertTrue(hasattr(tunnel, 'endpoint1'))
        self.assertTrue(hasattr(tunnel, 'endpoint2'))
        self.assertTrue(hasattr(tunnel, 'public_key'))

    def test_execute_mesh_health_consensus(self):
        consensus = self.mesh.execute_mesh_health_consensus()
        self.assertIsInstance(consensus, MeshHealthConsensus)
        self.assertTrue(consensus.quorum_reached)
        self.assertIsNotNone(consensus.consensus_hash)

    def test_detect_split_brain_no_partition(self):
        partitions = self.mesh.detect_split_brain()
        self.assertEqual(len(partitions), 0)

    def test_detect_split_brain_with_failure(self):
        node_id = list(self.mesh.nodes.keys())[0]
        self.mesh.nodes[node_id].state = MeshNodeState.FAILED
        partitions = self.mesh.detect_split_brain()
        self.assertGreater(len(partitions), 0)

    def test_resolve_split_brain_quorum(self):
        node_id = list(self.mesh.nodes.keys())[0]
        self.mesh.nodes[node_id].state = MeshNodeState.FAILED
        resolution = self.mesh.resolve_split_brain(strategy=SplitBrainStrategy.QUORUM)
        self.assertTrue(hasattr(resolution, 'resolved'))

    def test_execute_mesh_failover(self):
        node_id = list(self.mesh.nodes.keys())[0]
        target_id = list(self.mesh.nodes.keys())[1]
        self.mesh.nodes[node_id].state = MeshNodeState.FAILED
        
        event = self.mesh.execute_mesh_failover(failed_node_id=node_id, target_node_id=target_id)
        self.assertIsInstance(event, MeshFailoverEvent)
        self.assertTrue(event.pqc_verified)
        target_rto = getattr(self.mesh, 'target_rto_seconds', 300)
        self.assertLess(event.rto_seconds, target_rto)

    def test_execute_cross_region_dr_drill(self):
        report = self.mesh.execute_cross_region_dr_drill()
        self.assertTrue(hasattr(report, 'results'))
        self.assertEqual(len(report.results), len(self.mesh.nodes))

    def test_rotate_mesh_certificates(self):
        old_certs = {node_id: getattr(node, 'certificate_id', None) for node_id, node in self.mesh.nodes.items()}
        self.mesh.rotate_mesh_certificates()
        new_certs = {node_id: getattr(node, 'certificate_id', None) for node_id, node in self.mesh.nodes.items()}
        self.assertNotEqual(old_certs, new_certs)

    def test_get_mesh_topology_status(self):
        status = self.mesh.get_mesh_topology_status()
        self.assertIsInstance(status, dict)
        self.assertIn('nodes', status)
        self.assertIn('tunnels', status)
        self.assertIn('health', status)

if __name__ == "__main__":
    unittest.main()
