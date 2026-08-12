"""
Unit tests for High Availability (HA) Clustering & Failover Routing Engine.
"""

import unittest
from src.cluster.ha_failover import HAFailoverManager, NodeRole, NodeStatus


class TestHAFailoverManager(unittest.TestCase):
    """Test suite for HAFailoverManager."""

    def setUp(self):
        self.ha_mgr = HAFailoverManager()

    def test_initial_cluster_leader(self):
        leader = self.ha_mgr.get_active_leader()
        self.assertEqual(leader.node_id, "macmini-primary")
        self.assertEqual(leader.role, NodeRole.PRIMARY_LEADER)

    def test_manual_trigger_failover(self):
        new_leader = self.ha_mgr.trigger_failover("macmini-primary")
        self.assertEqual(new_leader.node_id, "macmini-secondary")
        self.assertEqual(new_leader.role, NodeRole.PRIMARY_LEADER)
        self.assertEqual(self.ha_mgr.nodes["macmini-primary"].status, NodeStatus.UNREACHABLE)

    def test_route_request_failover_fallback(self):
        # Set primary to unreachable to test automated failover during routing
        self.ha_mgr.nodes["macmini-primary"].status = NodeStatus.UNREACHABLE
        res = self.ha_mgr.route_request("/process-batch")

        self.assertEqual(res["ha_status"], "FAILOVER_EXECUTED")
        self.assertEqual(res["active_leader"], "macmini-secondary")


if __name__ == "__main__":
    unittest.main()
