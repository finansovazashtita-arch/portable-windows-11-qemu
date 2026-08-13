"""
Integration & Web UI tests for Poland KSeF e-Fakturowanie Dashboard Integration (M79).
"""

import os
import unittest
from src.dashboard.dashboard_server import WEB_UI_DIR


class TestKSeFDashboard(unittest.TestCase):
    """Test suite for Poland KSeF Web UI HTML page and integration assets."""

    def test_ksef_html_exists(self):
        ksef_html_path = os.path.join(WEB_UI_DIR, "ksef.html")
        self.assertTrue(os.path.exists(ksef_html_path), "ksef.html file must exist in web_ui directory")

    def test_ksef_html_content_validity(self):
        ksef_html_path = os.path.join(WEB_UI_DIR, "ksef.html")
        with open(ksef_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Poland KSeF e-Fakturowanie & GUS BIR Gateway (M79)", content)
        self.assertIn("FA(2) / FA(3) Structured XML Invoice Creator", content)
        self.assertIn("generateXMLPreview()", content)
        self.assertIn("submitToKSeF()", content)
        self.assertIn("searchGUS()", content)
        self.assertIn("/api/v1/ksef/invoices/submit", content)
        self.assertIn("/api/v1/ksef/gus/check", content)


if __name__ == "__main__":
    unittest.main()
