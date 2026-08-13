"""
Unit tests for Predictive AI Advisory Web UI Assets and Dashboard Server Integration (M77).
"""

import os
import unittest
from src.dashboard.dashboard_server import WEB_UI_DIR


class TestAdvisoryDashboardAssets(unittest.TestCase):
    """Test suite for Predictive AI Advisory Web UI dashboard static assets."""

    def test_advisory_html_exists(self):
        advisory_path = os.path.join(WEB_UI_DIR, "advisory.html")
        self.assertTrue(os.path.exists(advisory_path), "advisory.html should exist in WEB_UI_DIR")

    def test_advisory_html_content_structure(self):
        advisory_path = os.path.join(WEB_UI_DIR, "advisory.html")
        with open(advisory_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FinansProtect AI Advisory", content)
        self.assertIn("M77 PREDICTIVE ENGINE", content)
        self.assertIn("What-If Multi-Scenario Trajectory Simulator", content)
        self.assertIn("Prescriptive AI Recommendations", content)
        self.assertIn("Cash Conversion Cycle (CCC)", content)
        self.assertIn("Art. 96 VATA Registration Threshold", content)
        self.assertIn("/api/v1/advisory/insights", content)
        self.assertIn("/api/v1/advisory/cash-conversion-cycle", content)
        self.assertIn("/api/v1/advisory/tax-strategy", content)
        self.assertIn("/api/v1/advisory/export", content)


if __name__ == "__main__":
    unittest.main()
