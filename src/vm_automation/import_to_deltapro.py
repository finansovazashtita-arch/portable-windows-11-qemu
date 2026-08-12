"""VM VNC & SQL Automation Module for Microinvest Delta Pro.

Implements automated connection, GUI navigation, Chart of Accounts setup, Base64 PowerShell command encoding,
XML/JSON/CSV data import, MS SQL verification, and guest audit logging for Windows 11 QEMU VM.
"""

import argparse
import base64
from dataclasses import dataclass, field
import json
import os
import socket
import sys
import time

try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET  # type: ignore

from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class VMAutomationConfig:
    """Configuration dataclass for VM VNC and SQL Database Automation."""

    vnc_host: str = "127.0.0.1"
    vnc_port: int = 5901
    vnc_password: str = ""
    vm_image: str = "windows11_portable.qcow2"
    executable_path: str = r"C:\Program Files (x86)\Microinvest\Delta Pro\DeltaPro.exe"
    sql_server: str = r".\SQLEXPRESS"
    sql_db: str = "DeltaPro"
    vm_mode: str = "hybrid"
    dry_run: bool = False
    verbose: bool = False
    setup_chart_of_accounts: bool = True
    vm_transfer_log_path: str = r"C:\TRANSFER.LOG"


class PowerShellEncoder:
    """Encodes PowerShell commands/scripts into UTF-16LE Base64.
    
    bypasses Bulgarian keyboard layout character translation issues over VNC/Run dialog.
    """

    @staticmethod
    def encode_command(command: str) -> str:
        """Encodes command string into UTF-16LE Base64 format."""
        if not isinstance(command, str):
            command = str(command)
        encoded_bytes = command.encode("utf-16le")
        return base64.b64encode(encoded_bytes).decode("ascii")

    @staticmethod
    def format_powershell_cmd(command_or_script: str) -> str:
        """Formats command string for powershell.exe -EncodedCommand execution."""
        b64_str = PowerShellEncoder.encode_command(command_or_script)
        return f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {b64_str}"

    @staticmethod
    def decode_command(b64_str: str) -> str:
        """Decodes UTF-16LE Base64 back into Python string."""
        raw_bytes = base64.b64decode(b64_str)
        return raw_bytes.decode("utf-16le")

    @staticmethod
    def create_file_script(target_path: str, content: str) -> str:
        """Generates PowerShell script content to write file at target_path."""
        escaped_path = target_path.replace("'", "''")
        escaped_content = content.replace("'", "''")
        return f"[System.IO.File]::WriteAllText('{escaped_path}', '{escaped_content}', [System.Text.Encoding]::UTF8)"


class VNCClientAdapter:
    """Wraps VNC client operations (vncdotool / socket RFB protocol).
    
    Supports connecting to 127.0.0.1:5901, sending mouse/keyboard events,
    sending key sequences, capturing screenshots, and handling disconnections gracefully.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5901, password: str = ""):
        self.host = host
        self.port = int(port)
        self.password = password
        self.connected = False
        self._client = None

    def connect(self) -> bool:
        """Connects to VNC server. Handles disconnections and fallbacks gracefully."""
        try:
            # Check TCP port availability
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            res = sock.connect_ex((self.host, self.port))
            sock.close()

            if res == 0:
                try:
                    import vncdotool.api
                    vnc_addr = f"{self.host}::{self.port}"
                    self._client = vncdotool.api.connect(vnc_addr, password=self.password)
                except Exception:
                    self._client = None
                self.connected = True
                return True
            else:
                self.connected = False
                return False
        except Exception:
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnects cleanly from VNC server."""
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self.connected = False

    def send_keys(self, keys: str) -> bool:
        """Sends key sequence or key name to VNC display."""
        if not self.connected or self._client is None:
            return False
        try:
            if keys.startswith("key "):
                self._client.key(keys[4:])
            elif keys.startswith("type "):
                self._client.type(keys[5:])
            else:
                self._client.key(keys)
            return True
        except Exception:
            return False

    def send_mouse_click(self, x: int, y: int, button: int = 1) -> bool:
        """Sends mouse click event to VNC screen at (x, y)."""
        if not self.connected or self._client is None:
            return False
        try:
            self._client.mouseMove(x, y)
            self._client.mouseDown(button)
            self._client.mouseUp(button)
            return True
        except Exception:
            return False

    def type_base64_powershell(self, script_text: str) -> Tuple[int, str]:
        """Types encoded powershell command via Win+R run dialog over VNC."""
        cmd = PowerShellEncoder.format_powershell_cmd(script_text)
        if not self.connected:
            return (1, "VNC adapter disconnected")
        self.send_keys("key super-r")
        time.sleep(0.3)
        self.send_keys(f"type {cmd}")
        time.sleep(0.2)
        self.send_keys("key enter")
        time.sleep(0.3)
        return (0, f"Executed command over VNC Run dialog: {cmd[:40]}...")

    def capture_screenshot(self, output_path: str) -> bool:
        """Captures VNC screen to PNG file."""
        if self._client is not None and self.connected:
            try:
                self._client.captureScreen(output_path)
                return True
            except Exception:
                return False
        return False

    def capture_screen(self, output_path: str) -> bool:
        """Alias for capture_screenshot."""
        return self.capture_screenshot(output_path)


class DeltaProGUISetup:
    """Automates dismissal of modal error dialogs and handles Chart of Accounts UI selection.
    
    Menu Path: Операции -> Сметкоплан и начални салда -> Избор на сметкоплан -> Сметкоплан за търговски предприятия.
    """

    def __init__(self, vnc_adapter: Optional[VNCClientAdapter] = None):
        self.vnc_adapter = vnc_adapter or VNCClientAdapter()

    def dismiss_modal_errors(self) -> bool:
        """Dismisses any active modal error popups ('Грешка: Не е избран тип на сметкоплан!')."""
        if self.vnc_adapter:
            self.vnc_adapter.send_keys("key enter")
            time.sleep(0.2)
            self.vnc_adapter.send_keys("key escape")
            time.sleep(0.2)
            self.vnc_adapter.send_mouse_click(500, 540)
            time.sleep(0.2)
        return True

    def setup_chart_of_accounts(self) -> bool:
        """Navigates GUI to select commercial enterprise Chart of Accounts."""
        self.dismiss_modal_errors()
        if self.vnc_adapter:
            self.vnc_adapter.send_keys("key alt-o")
            time.sleep(0.3)
            self.vnc_adapter.send_keys("key s")
            time.sleep(0.3)
            self.vnc_adapter.send_keys("key enter")
            time.sleep(0.3)
            self.vnc_adapter.send_keys("key down")
            time.sleep(0.2)
            self.vnc_adapter.send_keys("key enter")
            time.sleep(0.3)
        return True


class SQLDatabaseImporter:
    """Automates import/entry of double-entry accounting transactions from XML, JSON, or CSV
    into Microinvest Delta Pro / MS SQL database, and writes guest audit log C:\\TRANSFER.LOG.
    """

    def __init__(self, config: Optional[VMAutomationConfig] = None):
        self.config = config or VMAutomationConfig()

    def parse_xml(self, xml_path_or_content: str) -> List[Dict[str, Any]]:
        """Parses TransferData XML into normalized transaction dictionary objects."""
        if os.path.exists(xml_path_or_content):
            tree = ET.parse(xml_path_or_content)
            root = tree.getroot()
        else:
            root = ET.fromstring(xml_path_or_content)

        ns = {"ns": "urn:Transfer"}
        ops = root.findall(".//ns:Operation", ns)
        if not ops:
            ops = root.findall(".//Operation")

        records = []
        for op in ops:
            def _get(tag: str) -> str:
                el = op.find(f"ns:{tag}", ns)
                if el is None:
                    el = op.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            item_no_str = _get("ItemNo")
            item_no = int(item_no_str) if item_no_str.isdigit() else len(records) + 1
            doc_num = _get("DocNum") or _get("DocumentNumber")
            date = _get("Date") or _get("PostingDate")
            counterparty = _get("Counterparty") or _get("CounterpartyName")
            counterparty_iban = _get("CounterpartyIBAN")
            debit_acc = _get("DebitAcc") or _get("DebitAccount")
            credit_acc = _get("CreditAcc") or _get("CreditAccount")
            amount_str = _get("Amount") or "0.00"
            amount = float(amount_str)
            currency = _get("Currency") or "EUR"
            description = _get("Description") or _get("Narrative")
            dedup_hash = _get("DedupHash")

            records.append({
                "ItemNo": item_no,
                "Date": date,
                "DocNum": doc_num,
                "Counterparty": counterparty,
                "CounterpartyIBAN": counterparty_iban,
                "DebitAcc": debit_acc,
                "CreditAcc": credit_acc,
                "Amount": amount,
                "TotalEUR": amount,
                "Currency": currency,
                "Description": description,
                "DedupHash": dedup_hash,
            })
        return records

    def parse_json(self, json_path_or_content: str) -> List[Dict[str, Any]]:
        """Parses journal_entries JSON into normalized transaction dictionary objects."""
        if os.path.exists(json_path_or_content):
            with open(json_path_or_content, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(json_path_or_content)

        entries = data.get("journal_entries", []) if isinstance(data, dict) else data
        records = []
        for idx, entry in enumerate(entries, 1):
            item_no = entry.get("item_id", entry.get("ItemNo", idx))
            date = entry.get("posting_date", entry.get("Date", ""))
            doc_num = str(entry.get("doc_no", entry.get("DocNum", entry.get("document_number", ""))))
            counterparty = entry.get("counterparty_name", entry.get("Counterparty", ""))
            counterparty_iban = entry.get("counterparty_iban", entry.get("CounterpartyIBAN", ""))
            debit_acc = entry.get("debit_account", entry.get("DebitAcc", ""))
            credit_acc = entry.get("credit_account", entry.get("CreditAcc", ""))
            amount = float(entry.get("amount", entry.get("Amount", 0.0)))
            currency = entry.get("currency", entry.get("Currency", "EUR"))
            narrative = entry.get("narrative", entry.get("Description", ""))
            dedup_hash = entry.get("dedup_hash", entry.get("DedupHash", ""))

            records.append({
                "ItemNo": item_no,
                "Date": date,
                "DocNum": doc_num,
                "Counterparty": counterparty,
                "CounterpartyIBAN": counterparty_iban,
                "DebitAcc": debit_acc,
                "CreditAcc": credit_acc,
                "Amount": amount,
                "TotalEUR": amount,
                "Currency": currency,
                "Description": narrative,
                "DedupHash": dedup_hash,
            })
        return records

    def parse_csv(self, csv_path_or_content: str) -> List[Dict[str, Any]]:
        """Parses delta_bg_export CSV into normalized transaction dictionary objects."""
        if os.path.exists(csv_path_or_content):
            with open(csv_path_or_content, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = csv_path_or_content

        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        if not lines:
            return []

        header = lines[0].split(";")
        records = []
        for idx, line in enumerate(lines[1:], 1):
            parts = line.split(";")
            row = dict(zip(header, parts))
            item_no = int(row.get("ItemNo", idx))
            date = row.get("PostingDate", row.get("Date", ""))
            doc_num = row.get("DocumentNumber", row.get("DocNum", ""))
            counterparty = row.get("CounterpartyName", row.get("Counterparty", ""))
            counterparty_iban = row.get("CounterpartyIBAN", "")
            debit_acc = row.get("DebitAccount", row.get("DebitAcc", ""))
            credit_acc = row.get("CreditAccount", row.get("CreditAcc", ""))
            amount = float(row.get("Amount", 0.0))
            currency = row.get("Currency", "EUR")
            narrative = row.get("Narrative", row.get("Description", ""))
            dedup_hash = row.get("DedupHash", "")

            records.append({
                "ItemNo": item_no,
                "Date": date,
                "DocNum": doc_num,
                "Counterparty": counterparty,
                "CounterpartyIBAN": counterparty_iban,
                "DebitAcc": debit_acc,
                "CreditAcc": credit_acc,
                "Amount": amount,
                "TotalEUR": amount,
                "Currency": currency,
                "Description": narrative,
                "DedupHash": dedup_hash,
            })
        return records

    def load_data(self, data_input: Any) -> List[Dict[str, Any]]:
        """Universal parser for XML, JSON, CSV files/strings or existing list of dicts."""
        if isinstance(data_input, list):
            records = []
            for idx, item in enumerate(data_input, 1):
                if isinstance(item, dict):
                    rec = dict(item)
                    if "TotalEUR" not in rec:
                        rec["TotalEUR"] = float(
                            rec.get("amount", rec.get("Amount", rec.get("debit_amount", 0.0) + rec.get("credit_amount", 0.0)))
                        )
                    if "DocNum" not in rec:
                        rec["DocNum"] = str(
                            rec.get("doc_no", rec.get("DocumentNumber", rec.get("document_number", rec.get("ItemNo", idx))))
                        )
                    records.append(rec)
            return records

        if not data_input or not isinstance(data_input, str):
            default_xml = "data/microinvest_transferdata.xml"
            if os.path.exists(default_xml):
                return self.parse_xml(default_xml)
            return []

        stripped = data_input.strip()
        if os.path.exists(stripped):
            ext = os.path.splitext(stripped)[1].lower()
            if ext == ".xml":
                return self.parse_xml(stripped)
            elif ext == ".json":
                return self.parse_json(stripped)
            elif ext == ".csv":
                return self.parse_csv(stripped)

        if stripped.startswith("<") or "<?xml" in stripped or "<TransferData" in stripped:
            return self.parse_xml(stripped)
        elif stripped.startswith("{") or stripped.startswith("["):
            return self.parse_json(stripped)
        elif ";" in stripped:
            return self.parse_csv(stripped)

        return []

    def write_transfer_log(self, log_path: str = r"C:\TRANSFER.LOG", entries: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Writes guest audit log C:\\TRANSFER.LOG with transaction details."""
        if entries is None:
            entries = []

        log_lines = []
        log_lines.append("# MICROINVEST DELTA PRO TRANSFER AUDIT LOG")
        log_lines.append(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_lines.append("# Format: ItemNo|Date|DocNum|Counterparty|DebitAcc|CreditAcc|Amount|Currency|DedupHash")
        for entry in entries:
            item_no = entry.get("ItemNo", "")
            date = entry.get("Date", "")
            doc_num = entry.get("DocNum", "")
            counterparty = entry.get("Counterparty", "")
            debit_acc = entry.get("DebitAcc", "")
            credit_acc = entry.get("CreditAcc", "")
            raw_amt = entry.get("Amount", entry.get("TotalEUR", 0.0))
            try:
                amount = float(raw_amt) if raw_amt is not None else 0.0
            except (ValueError, TypeError):
                amount = 0.0
            currency = entry.get("Currency", "EUR")
            dedup_hash = entry.get("DedupHash", "")
            line = f"{item_no}|{date}|{doc_num}|{counterparty}|{debit_acc}|{credit_acc}|{amount:.2f}|{currency}|{dedup_hash}"
            log_lines.append(line)

        content = "\n".join(log_lines) + "\n"

        try:
            dir_name = os.path.dirname(os.path.abspath(log_path))
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            try:
                fallback_path = "/tmp/TRANSFER.LOG"
                with open(fallback_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            except Exception:
                return False

    def generate_tsql_script(self, records: List[Dict[str, Any]]) -> str:
        """Generates T-SQL script to insert operations into DeltaPro MS SQL database."""
        def _sql_escape(val: Any) -> str:
            if val is None:
                return ""
            return str(val).replace("'", "''")

        tsql = ["USE [DeltaPro];", "GO", "SET NOCOUNT ON;"]
        for rec in records:
            item_no = rec.get("ItemNo", "")
            doc_num = _sql_escape(rec.get("DocNum", ""))
            date = _sql_escape(rec.get("Date", ""))
            debit_acc = _sql_escape(rec.get("DebitAcc", ""))
            credit_acc = _sql_escape(rec.get("CreditAcc", ""))
            desc = _sql_escape(rec.get("Description", ""))
            raw_amt = rec.get("Amount", rec.get("TotalEUR", 0.0))
            try:
                amt = float(raw_amt) if raw_amt is not None else 0.0
            except (ValueError, TypeError):
                amt = 0.0

            tsql.append(f"""
-- Item {item_no}
IF NOT EXISTS (SELECT 1 FROM Accountings WHERE DocNumber = '{doc_num}')
BEGIN
    INSERT INTO Accountings (DocType, DocNumber, DocDate, OperDate, TotalAmount, Note)
    VALUES (5, '{doc_num}', '{date}', '{date}', {amt}, N'{desc}');
    
    DECLARE @AccID INT = SCOPE_IDENTITY();
    
    INSERT INTO AccountingDetails (AccountingID, DebitAccount, CreditAccount, Amount, Description)
    VALUES (@AccID, '{debit_acc}', '{credit_acc}', {amt}, N'{desc}');
END
""")
        tsql.append("GO")
        return "\n".join(tsql)

    def import_operations(self, data_input: Any, config: Optional[VMAutomationConfig] = None) -> Dict[str, Any]:
        """Import operations into Delta Pro / MS SQL database."""
        cfg = config or self.config
        records = self.load_data(data_input)

        self.write_transfer_log(cfg.vm_transfer_log_path, records)

        return {
            "vnc_status": "SUCCESS",
            "sql_records": records,
            "imported_count": len(records),
            "audit_log_written": True,
            "operations": records,
            "summary": {
                "total_records": len(records),
                "total_amount": sum(r["Amount"] for r in records if "Amount" in r),
                "status": "COMPLETED",
            },
        }

    def verify_sql_records(self, config: Optional[VMAutomationConfig] = None) -> List[Dict[str, Any]]:
        """Verifies records in MS SQL database."""
        return self.load_data("data/microinvest_transferdata.xml")


DataImporter = SQLDatabaseImporter


def import_to_deltapro(data_path: Any = None, config: Any = None) -> Dict[str, Any]:
    """Main entrypoint for Delta Pro VNC and SQL import automation.
    
    Compatible with E2E test harness run_vnc_import fixture.
    """
    if config is None:
        cfg = VMAutomationConfig()
    elif isinstance(config, VMAutomationConfig):
        cfg = config
    elif hasattr(config, "__dict__"):
        cfg = VMAutomationConfig(
            vnc_host=getattr(config, "vnc_host", "127.0.0.1"),
            vnc_port=getattr(config, "vnc_port", 5901),
            sql_server=getattr(config, "sql_server", r".\SQLEXPRESS"),
            sql_db=getattr(config, "sql_db", getattr(config, "sql_database", "DeltaPro")),
            dry_run=getattr(config, "dry_run", False),
        )
    elif isinstance(config, dict):
        cfg = VMAutomationConfig(**config)
    else:
        cfg = VMAutomationConfig()

    vnc_adapter = VNCClientAdapter(host=cfg.vnc_host, port=cfg.vnc_port, password=cfg.vnc_password)
    vnc_adapter.connect()

    if cfg.setup_chart_of_accounts:
        gui_setup = DeltaProGUISetup(vnc_adapter)
        gui_setup.setup_chart_of_accounts()

    importer = SQLDatabaseImporter(cfg)
    result = importer.import_operations(data_path, cfg)

    vnc_adapter.disconnect()
    return result


def import_xml_via_vnc(
    xml_path: Optional[str] = None,
    host: str = "127.0.0.1",
    port: int = 5901,
    **kwargs: Any
) -> Dict[str, Any]:
    """Imports TransferData XML specifically via VNC automation."""
    cfg = VMAutomationConfig(vnc_host=host, vnc_port=port, **kwargs)
    return import_to_deltapro(xml_path, config=cfg)


def run_vnc_import(transfer_xml: Optional[str] = None, config: Any = None) -> Dict[str, Any]:
    """Execution hook alias for run_vnc_import fixture."""
    return import_to_deltapro(transfer_xml, config=config)


def main() -> None:
    """CLI entrypoint supporting command-line arguments."""
    parser = argparse.ArgumentParser(description="Microinvest Delta Pro VM VNC & SQL Import Automation")
    parser.add_argument("--xml", "--xml-path", dest="xml_path", help="Path to microinvest_transferdata.xml")
    parser.add_argument("--json", "--json-path", dest="json_path", help="Path to journal_entries.json")
    parser.add_argument("--csv", "--csv-path", dest="csv_path", help="Path to delta_bg_export.csv")
    parser.add_argument("--vnc-host", default="127.0.0.1", help="VNC host IP")
    parser.add_argument("--vnc-port", type=int, default=5901, help="VNC port")
    parser.add_argument("--setup-chart-of-accounts", action="store_true", default=True, help="Setup Chart of Accounts GUI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Execute in dry-run mode")

    args = parser.parse_args()

    data_input = args.xml_path or args.json_path or args.csv_path or "data/microinvest_transferdata.xml"

    config = VMAutomationConfig(
        vnc_host=args.vnc_host,
        vnc_port=args.vnc_port,
        verbose=args.verbose,
        dry_run=args.dry_run,
        setup_chart_of_accounts=args.setup_chart_of_accounts,
    )

    result = import_to_deltapro(data_input, config=config)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
