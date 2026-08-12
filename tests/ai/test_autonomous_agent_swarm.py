"""
Unit tests for Sovereign Autonomous Enterprise AI Agent Swarm Engine.
"""

import unittest

from src.ai.autonomous_agent_swarm import AgentRole, AgentStatus, AutonomousAgentSwarm


class TestAutonomousAgentSwarm(unittest.TestCase):
    """Test suite for AutonomousAgentSwarm."""

    def setUp(self):
        self.swarm = AutonomousAgentSwarm()

    def test_swarm_initialization(self):
        health = self.swarm.get_swarm_health()
        self.assertEqual(health["healthy_count"], 4)
        self.assertEqual(health["total_agents"], 4)
        self.assertEqual(health["swarm_health_ratio"], 1.0)

    def test_start_swarm_cycle(self):
        res = self.swarm.start_swarm_cycle()
        self.assertEqual(res["swarm_status"], "OPERATIONAL_24_7")
        self.assertEqual(res["active_agents"], 4)
        self.assertIn("AUDITOR_AGENT", res["cycle_results"])

    def test_trigger_self_healing(self):
        success = self.swarm.trigger_self_healing(AgentRole.FRAUD_GUARD_AGENT)
        self.assertTrue(success)
        health = self.swarm.get_swarm_health()
        self.assertEqual(health["agent_states"]["FRAUD_GUARD_AGENT"], "HEALTHY")


if __name__ == "__main__":
    unittest.main()
