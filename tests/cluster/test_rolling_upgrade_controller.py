"""
Unit tests for Zero-Downtime Live Production Rolling Upgrade Controller Engine.
"""

import unittest

from src.cluster.rolling_upgrade_controller import RollingUpgradeController, UpgradeState


class TestRollingUpgradeController(unittest.TestCase):
    """Test suite for RollingUpgradeController."""

    def setUp(self):
        self.controller = RollingUpgradeController()

    def test_execute_rolling_upgrade_success(self):
        res = self.controller.execute_rolling_upgrade("macmini-primary", "v2.0.0")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["version"], "v2.0.0")

    def test_execute_rolling_upgrade_rollback(self):
        res = self.controller.execute_rolling_upgrade("macmini-secondary", "v2.1.0-bad", simulate_failure=True)
        self.assertEqual(res["status"], "ROLLED_BACK")


if __name__ == "__main__":
    unittest.main()
