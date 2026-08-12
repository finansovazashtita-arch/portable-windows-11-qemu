"""
Unit tests for FinansProtect Web UI Dashboard Server.
"""

import os
import unittest
from src.dashboard.dashboard_server import WEB_UI_DIR


class TestDashboardServer(unittest.TestCase):
    """Test suite for FinansProtect Web UI Dashboard static assets."""

    def test_web_ui_assets_exist(self):
        index_path = os.path.join(WEB_UI_DIR, "index.html")
        css_path = os.path.join(WEB_UI_DIR, "styles.css")
        js_path = os.path.join(WEB_UI_DIR, "app.js")

        self.assertTrue(os.path.exists(index_path))
        self.assertTrue(os.path.exists(css_path))
        self.assertTrue(os.path.exists(js_path))

    def test_index_html_structure(self):
        index_path = os.path.join(WEB_UI_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FinansProtect", content)
        self.assertIn("Microinvest Delta Pro", content)
        self.assertIn("QEMU Windows 11 VM", content)
        self.assertIn("Банка ДСК", content)
        self.assertIn("УниКредит", content)
        self.assertIn("ОББ", content)
        self.assertIn("Пощенска", content)


if __name__ == "__main__":
    unittest.main()
