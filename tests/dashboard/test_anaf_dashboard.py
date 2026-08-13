"""
Integration & Web UI tests for Romania ANAF e-Factura Dashboard Integration (M78).
"""

import os
import unittest
from src.dashboard.dashboard_server import WEB_UI_DIR


class TestANAFDashboard(unittest.TestCase):
    """Test suite for ANAF Web UI HTML page and integration assets."""

    def test_anaf_html_exists(self):
        anaf_html_path = os.path.join(WEB_UI_DIR, "anaf.html")
        self.assertTrue(os.path.exists(anaf_html_path), "anaf.html file must exist in web_ui directory")

    def test_anaf_html_content_validity(self):
        anaf_html_path = os.path.join(WEB_UI_DIR, "anaf.html")
        with open(anaf_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Romania ANAF e-Factura Gateway", content)
        self.assertIn("RO-CIUS 1.0.1", content)
        self.assertIn("generateXML()", content)
        self.assertIn("checkVATRegistry()", content)
        self.assertIn("/api/v1/anaf/invoices/submit", content)


if __name__ == "__main__":
    unittest.main()
