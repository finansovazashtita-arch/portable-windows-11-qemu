"""
Unit tests for Distributed AI Multi-Node GPU Cluster Orchestrator Engine.
"""

import unittest

from src.ai.gpu_cluster_orchestrator import DistributedGPUClusterOrchestrator, GPUNode, InferenceBackend


class TestDistributedGPUClusterOrchestrator(unittest.TestCase):
    """Test suite for DistributedGPUClusterOrchestrator."""

    def setUp(self):
        self.orchestrator = DistributedGPUClusterOrchestrator()

    def test_get_best_healthy_node(self):
        node = self.orchestrator.get_best_healthy_node()
        self.assertTrue(node.is_healthy)
        self.assertIn(node.backend, [InferenceBackend.OLLAMA, InferenceBackend.VLLM])

    def test_dispatch_classification_request(self):
        res = self.orchestrator.dispatch_classification_request("Плащане фактура 10002489")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["predicted_account_dr"], "503")
        self.assertGreater(res["confidence_score"], 0.9)

    def test_fallback_when_all_nodes_unhealthy(self):
        for n in self.orchestrator.nodes:
            n.is_healthy = False

        node = self.orchestrator.get_best_healthy_node()
        self.assertEqual(node.backend, InferenceBackend.LOCAL_FALLBACK)

    def test_get_cluster_status(self):
        status = self.orchestrator.get_cluster_status()
        self.assertEqual(status["total_nodes"], 2)
        self.assertEqual(status["healthy_nodes"], 2)


if __name__ == "__main__":
    unittest.main()
