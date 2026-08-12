"""Unit and Integration Test Suite for VM VNC & SQL Automation Module (src/vm_automation/import_to_deltapro.py)."""

import base64
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pytest

from src.vm_automation.import_to_deltapro import (
    VMAutomationConfig,
    PowerShellEncoder,
    VNCClientAdapter,
    DeltaProGUISetup,
    SQLDatabaseImporter,
    DataImporter,
    import_to_deltapro,
    import_xml_via_vnc,
    run_vnc_import,
    main,
)


class TestVMAutomationConfig(unittest.TestCase):
    """Tests for VMAutomationConfig initialization and default values."""

    def test_default_config_values(self):
        config = VMAutomationConfig()
        self.assertEqual(config.vnc_host, "127.0.0.1")
        self.assertEqual(config.vnc_port, 5901)
        self.assertEqual(config.vnc_password, "")
        self.assertEqual(config.vm_image, "windows11_portable.qcow2")
        self.assertEqual(config.executable_path, r"C:\Program Files (x86)\Microinvest\Delta Pro\DeltaPro.exe")
        self.assertEqual(config.sql_server, r".\SQLEXPRESS")
        self.assertEqual(config.sql_db, "DeltaPro")
        self.assertEqual(config.vm_mode, "hybrid")
        self.assertFalse(config.dry_run)
        self.assertFalse(config.verbose)
        self.assertTrue(config.setup_chart_of_accounts)
        self.assertEqual(config.vm_transfer_log_path, r"C:\TRANSFER.LOG")

    def test_custom_config_values(self):
        config = VMAutomationConfig(
            vnc_host="192.168.1.100",
            vnc_port=5902,
            vnc_password="secretpassword",
            sql_server=r"localhost\SQLEXPRESS",
            sql_db="CustomDB",
            dry_run=True,
            verbose=True,
            setup_chart_of_accounts=False,
        )
        self.assertEqual(config.vnc_host, "192.168.1.100")
        self.assertEqual(config.vnc_port, 5902)
        self.assertEqual(config.vnc_password, "secretpassword")
        self.assertEqual(config.sql_db, "CustomDB")
        self.assertTrue(config.dry_run)
        self.assertTrue(config.verbose)
        self.assertFalse(config.setup_chart_of_accounts)


class TestPowerShellEncoder(unittest.TestCase):
    """Tests for PowerShellEncoder UTF-16LE Base64 encoding and command formatting."""

    def test_encode_command(self):
        cmd = "Get-Service MSSQLSERVER"
        encoded = PowerShellEncoder.encode_command(cmd)
        self.assertIsInstance(encoded, str)
        # Verify base64 string
        decoded_bytes = base64.b64decode(encoded)
        decoded_str = decoded_bytes.decode("utf-16le")
        self.assertEqual(decoded_str, cmd)

    def test_format_powershell_cmd(self):
        cmd = "Write-Host 'Hello World'"
        ps_cmd = PowerShellEncoder.format_powershell_cmd(cmd)
        self.assertTrue(ps_cmd.startswith("powershell.exe -NoProfile -NonInteractive -EncodedCommand "))
        b64_part = ps_cmd.split("-EncodedCommand ")[1]
        decoded = PowerShellEncoder.decode_command(b64_part)
        self.assertEqual(decoded, cmd)

    def test_decode_command(self):
        original = "Test String UTF16LE български текст 123"
        b64_encoded = PowerShellEncoder.encode_command(original)
        decoded = PowerShellEncoder.decode_command(b64_encoded)
        self.assertEqual(decoded, original)

    def test_create_file_script(self):
        target = r"C:\TRANSFER.LOG"
        content = "Line 1\nLine 2"
        script = PowerShellEncoder.create_file_script(target, content)
        self.assertIn("[System.IO.File]::WriteAllText", script)
        self.assertIn("TRANSFER.LOG", script)
        self.assertIn("UTF8", script)


class TestVNCClientAdapter(unittest.TestCase):
    """Tests for VNCClientAdapter socket/vncdotool interaction and error handling."""

    def test_adapter_initialization(self):
        adapter = VNCClientAdapter("127.0.0.1", 5901, "password")
        self.assertEqual(adapter.host, "127.0.0.1")
        self.assertEqual(adapter.port, 5901)
        self.assertEqual(adapter.password, "password")
        self.assertFalse(adapter.connected)

    @patch("socket.socket")
    def test_connect_failure(self, mock_socket_class):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_socket_class.return_value = mock_sock

        adapter = VNCClientAdapter("127.0.0.1", 5999)
        result = adapter.connect()
        self.assertFalse(result)
        self.assertFalse(adapter.connected)

    @patch("socket.socket")
    def test_connect_success(self, mock_socket_class):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Success
        mock_socket_class.return_value = mock_sock

        adapter = VNCClientAdapter("127.0.0.1", 5901)
        result = adapter.connect()
        self.assertTrue(result)
        self.assertTrue(adapter.connected)
        adapter.disconnect()
        self.assertFalse(adapter.connected)

    def test_send_keys_and_mouse_clicks(self):
        adapter = VNCClientAdapter("127.0.0.1", 5901)
        adapter.connected = True
        adapter._client = MagicMock()
        self.assertTrue(adapter.send_keys("key enter"))
        self.assertTrue(adapter.send_keys("type hello"))
        self.assertTrue(adapter.send_mouse_click(100, 200))

    def test_type_base64_powershell(self):
        adapter = VNCClientAdapter("127.0.0.1", 5901)
        adapter.connected = True
        adapter._client = MagicMock()
        code, msg = adapter.type_base64_powershell("Get-Process")
        self.assertEqual(code, 0)
        self.assertIn("Executed command over VNC Run dialog", msg)

    def test_capture_screenshot(self):
        adapter = VNCClientAdapter("127.0.0.1", 5901)
        res = adapter.capture_screenshot("/tmp/test_capture.png")
        self.assertIsInstance(res, bool)


class TestDeltaProGUISetup(unittest.TestCase):
    """Tests for DeltaProGUISetup modal dialog handling and navigation sequence."""

    def test_dismiss_modal_errors(self):
        mock_vnc = MagicMock()
        gui_setup = DeltaProGUISetup(mock_vnc)
        res = gui_setup.dismiss_modal_errors()
        self.assertTrue(res)
        mock_vnc.send_keys.assert_any_call("key enter")
        mock_vnc.send_keys.assert_any_call("key escape")
        mock_vnc.send_mouse_click.assert_called_with(500, 540)

    def test_setup_chart_of_accounts(self):
        mock_vnc = MagicMock()
        gui_setup = DeltaProGUISetup(mock_vnc)
        res = gui_setup.setup_chart_of_accounts()
        self.assertTrue(res)
        mock_vnc.send_keys.assert_any_call("key alt-o")
        mock_vnc.send_keys.assert_any_call("key s")
        mock_vnc.send_keys.assert_any_call("key enter")
        mock_vnc.send_keys.assert_any_call("key down")


class TestSQLDatabaseImporter(unittest.TestCase):
    """Tests for SQLDatabaseImporter / DataImporter parsing and audit logging."""

    def setUp(self):
        self.importer = SQLDatabaseImporter()

    def test_parse_xml_file(self):
        xml_path = "data/microinvest_transferdata.xml"
        if os.path.exists(xml_path):
            records = self.importer.parse_xml(xml_path)
            self.assertEqual(len(records), 21)
            first = records[0]
            self.assertEqual(first["ItemNo"], 1)
            self.assertEqual(first["DocNum"], "12101")
            self.assertEqual(first["Counterparty"], "НАП")
            self.assertEqual(first["DebitAcc"], "455")
            self.assertEqual(first["CreditAcc"], "503")
            self.assertEqual(first["Amount"], 44.05)
            self.assertEqual(first["TotalEUR"], 44.05)

    def test_parse_json_file(self):
        json_path = "data/journal_entries.json"
        if os.path.exists(json_path):
            records = self.importer.parse_json(json_path)
            self.assertEqual(len(records), 21)
            first = records[0]
            self.assertEqual(first["ItemNo"], 1)
            self.assertEqual(first["DocNum"], "12101")
            self.assertEqual(first["Counterparty"], "НАП")
            self.assertEqual(first["Amount"], 44.05)

    def test_parse_csv_file(self):
        csv_path = "data/delta_bg_export.csv"
        if os.path.exists(csv_path):
            records = self.importer.parse_csv(csv_path)
            self.assertEqual(len(records), 21)
            first = records[0]
            self.assertEqual(first["ItemNo"], 1)
            self.assertEqual(first["DocNum"], "12101")
            self.assertEqual(first["Counterparty"], "НАП")
            self.assertEqual(first["Amount"], 44.05)

    def test_load_data_universal(self):
        # Test with list of dicts
        sample_dicts = [
            {"ItemNo": 1, "DocNum": "1001", "Amount": 150.0, "DebitAcc": "503", "CreditAcc": "401"},
            {"ItemNo": 2, "DocNum": "1002", "Amount": 250.0, "DebitAcc": "621", "CreditAcc": "503"},
        ]
        recs = self.importer.load_data(sample_dicts)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["TotalEUR"], 150.0)

        # Test with XML file path
        if os.path.exists("data/microinvest_transferdata.xml"):
            xml_recs = self.importer.load_data("data/microinvest_transferdata.xml")
            self.assertEqual(len(xml_recs), 21)

    def test_write_transfer_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "TRANSFER.LOG")
            sample_records = [
                {
                    "ItemNo": 1,
                    "Date": "2026-01-05",
                    "DocNum": "12101",
                    "Counterparty": "НАП",
                    "DebitAcc": "455",
                    "CreditAcc": "503",
                    "Amount": 44.05,
                    "Currency": "EUR",
                    "DedupHash": "21252876483e5d8e64071495ee23c5ea61f97eb875f8c0d36937ce1ed20713c1",
                }
            ]
            res = self.importer.write_transfer_log(log_file, sample_records)
            self.assertTrue(res)
            self.assertTrue(os.path.exists(log_file))

            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("MICROINVEST DELTA PRO TRANSFER AUDIT LOG", content)
            self.assertIn("12101", content)
            self.assertIn("НАП", content)
            self.assertIn("44.05", content)

    def test_generate_tsql_script(self):
        sample_records = [
            {
                "ItemNo": 1,
                "Date": "2026-01-05",
                "DocNum": "12101",
                "Counterparty": "НАП",
                "DebitAcc": "455",
                "CreditAcc": "503",
                "Amount": 44.05,
                "Description": "NCC WITHDRAWAL 12101",
            }
        ]
        tsql = self.importer.generate_tsql_script(sample_records)
        self.assertIn("USE [DeltaPro];", tsql)
        self.assertIn("DocNumber = '12101'", tsql)
        self.assertIn("INSERT INTO Accountings", tsql)


class TestImportEntrypoints(unittest.TestCase):
    """Tests for top-level entrypoint functions and CLI execution."""

    def test_import_to_deltapro(self):
        res = import_to_deltapro("data/microinvest_transferdata.xml")
        self.assertEqual(res["vnc_status"], "SUCCESS")
        self.assertIn("sql_records", res)
        self.assertEqual(len(res["sql_records"]), 21)
        self.assertEqual(res["imported_count"], 21)
        self.assertTrue(res["audit_log_written"])

    def test_import_xml_via_vnc(self):
        res = import_xml_via_vnc("data/microinvest_transferdata.xml", host="127.0.0.1", port=5901)
        self.assertEqual(res["vnc_status"], "SUCCESS")
        self.assertEqual(len(res["sql_records"]), 21)

    def test_run_vnc_import_alias(self):
        res = run_vnc_import("data/microinvest_transferdata.xml")
        self.assertEqual(res["vnc_status"], "SUCCESS")
        self.assertEqual(len(res["sql_records"]), 21)

    @patch("sys.argv", ["import_to_deltapro.py", "--dry-run", "--verbose"])
    def test_cli_main(self):
        try:
            main()
        except SystemExit as e:
            self.assertEqual(e.code, 0)


if __name__ == "__main__":
    unittest.main()
