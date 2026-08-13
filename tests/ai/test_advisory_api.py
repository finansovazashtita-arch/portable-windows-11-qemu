"""
Unit tests for Predictive AI Advisory REST API handlers (M77).
"""

import json
import unittest

from src.ai.advisory_api import (
    export_advisory_report_handler,
    get_advisory_insights_handler,
    get_cash_conversion_cycle_handler,
    get_tax_strategy_handler,
    run_scenario_simulation_handler,
)


class TestAdvisoryAPIHandlers(unittest.TestCase):
    """Test suite for Predictive AI Advisory REST API router."""

    def setUp(self):
        self.tenant_id = "tenant-api-test-01"

    def test_get_advisory_insights_handler(self):
        res = get_advisory_insights_handler({"tenant_id": self.tenant_id})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["tenant_id"], self.tenant_id)
        self.assertGreater(res["total_insights"], 0)
        self.assertIsInstance(res["insights"], list)

    def test_run_scenario_simulation_handler(self):
        payload = {"tenant_id": self.tenant_id, "horizon_days": 60}
        res = run_scenario_simulation_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["simulation"]["horizon_days"], 60)
        self.assertIn("scenarios", res["simulation"])

    def test_get_cash_conversion_cycle_handler(self):
        res = get_cash_conversion_cycle_handler({"tenant_id": self.tenant_id})
        self.assertEqual(res["status"], "success")
        self.assertIn("cash_conversion_cycle", res)
        self.assertIn("ccc_days", res["cash_conversion_cycle"])

    def test_get_tax_strategy_handler(self):
        res = get_tax_strategy_handler({"tenant_id": self.tenant_id})
        self.assertEqual(res["status"], "success")
        self.assertIn("tax_strategy", res)
        self.assertEqual(res["tax_strategy"]["vat_threshold_bgn"], 100000.0)

    def test_export_advisory_report_handler_json(self):
        payload = {"tenant_id": self.tenant_id, "format": "JSON"}
        res = export_advisory_report_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["format"], "JSON")
        self.assertIn("content", res)

    def test_export_advisory_report_handler_csv(self):
        payload = {"tenant_id": self.tenant_id, "format": "CSV"}
        res = export_advisory_report_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["format"], "CSV")
        self.assertTrue(res["content"].startswith("id,tenant_id,title"))

    def test_export_advisory_report_handler_pdf(self):
        payload = {"tenant_id": self.tenant_id, "format": "PDF"}
        res = export_advisory_report_handler(payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["format"], "PDF")
        self.assertIn("pdf_summary", res)


if __name__ == "__main__":
    unittest.main()
