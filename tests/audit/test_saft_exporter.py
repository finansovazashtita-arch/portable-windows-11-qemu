"""
Unit tests for OECD SAF-T & NRA Tax Audit Exporter Module.
"""

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from src.audit.saft_exporter import SAFTExporter


class TestSAFTExporter(unittest.TestCase):
    """Test suite for SAFTExporter."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_path = os.path.join(self.temp_dir.name, "SAF-T_Audit_File.xml")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_saft_xml_structure(self):
        company_info = {
            "company_name": "СТОРГОЗИЯ АД",
            "eik": "114077876",
            "currency": "EUR",
        }
        journal_entries = [
            {
                "date": "2026-01-10",
                "narrative": "Такса обслужване банкова сметка",
                "lines": [
                    {"account_code": "621", "amount": 5.50, "type": "DEBIT"},
                    {"account_code": "503", "amount": 5.50, "type": "CREDIT"},
                ],
            }
        ]

        file_path = SAFTExporter.generate_saft_xml(company_info, journal_entries, self.output_path)
        self.assertTrue(os.path.exists(file_path))

        tree = ET.parse(file_path)
        root = tree.getroot()

        self.assertIn("AuditFile", root.tag)
        header = root.find("{urn:OECD:StandardAuditFile-Tax:2.00}Header")
        self.assertIsNotNone(header)

        gl_entries = root.find("{urn:OECD:StandardAuditFile-Tax:2.00}GeneralLedgerEntries")
        self.assertIsNotNone(gl_entries)

        num_entries = gl_entries.find("{urn:OECD:StandardAuditFile-Tax:2.00}NumberOfEntries")
        self.assertEqual(num_entries.text, "1")


if __name__ == "__main__":
    unittest.main()
