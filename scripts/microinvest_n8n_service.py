#!/usr/bin/env python3
"""
Microinvest Bank Statement OCR & Delta Pro Automation Service with Full Infrastructure Integration:
- Infisical Vault Secrets Management
- Unsloth.ai LLM Transaction Classification
- Obsidian Vault Self-Hosted Note Sync
- Supabase Database Audit Logging
- OpenBalancer Dashboard Telemetry
- QEMU Windows 11 VM (Microinvest Delta Pro & MS SQL Server) VNC Import
"""

import http.server
import json
import os
import subprocess
import sys

# Ensure src package is importable
WORK_DIR = "/Users/diokarabaz/MICROINVEST-OCR"
if not os.path.exists(WORK_DIR):
    WORK_DIR = "/Users/diokarabaz/orca/workspaces/2026-08-05/работно-пространство"

if WORK_DIR not in sys.path:
    sys.path.insert(0, WORK_DIR)

from src.ai.unsloth_classifier import UnslothTransactionClassifier
from src.dashboard.openbalancer_client import OpenBalancerClient
from src.integration.obsidian_exporter import ObsidianVaultExporter
from src.integration.supabase_logger import SupabaseLogger
from src.security.infisical_vault import InfisicalVaultClient

PORT = 8090
DEFAULT_PDF = f"{WORK_DIR}/data/1.pdf"

# Initialize Infrastructure Clients
VAULT_CLIENT = InfisicalVaultClient()
AI_CLASSIFIER = UnslothTransactionClassifier()
OBSIDIAN_EXPORTER = ObsidianVaultExporter()
SUPABASE_LOGGER = SupabaseLogger()
TELEMETRY_CLIENT = OpenBalancerClient()


class StatementHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        pdf_path = payload.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            pdf_path = DEFAULT_PDF

        python_bin = sys.executable

        json_out = "/tmp/extracted_transactions.json"
        xml_out = "/tmp/microinvest_transferdata.xml"
        journal_out = "/tmp/journal_entries.json"
        audit_out = "/tmp/TRANSFER.LOG"

        # Fetch secrets securely from Infisical Vault
        vm_creds = VAULT_CLIENT.get_vm_credentials()

        # Execute Pipeline Steps
        ocr_cmd = [python_bin, f"{WORK_DIR}/src/ocr/extract_dsk_statement.py", "--pdf-path", pdf_path, "--output", json_out]
        trans_cmd = [python_bin, f"{WORK_DIR}/src/accounting/translate_to_delta.py", "--input", json_out, "--output-dir", "/tmp"]
        vm_cmd = [python_bin, f"{WORK_DIR}/src/vm_automation/import_to_deltapro.py", "--xml", xml_out]
        audit_cmd = [python_bin, f"{WORK_DIR}/src/audit/generate_transfer_log.py", "--json-path", journal_out, "--output-path", audit_out]

        try:
            # 1. PDF OCR Extraction
            subprocess.run(ocr_cmd, capture_output=True, text=True, check=True)

            # 2. Unsloth AI Classification & Double-Entry Accounting Translation
            with open(json_out, "r", encoding="utf-8") as f:
                extracted_data = json.load(f)

            transactions = extracted_data.get("transactions", [])
            ai_enriched_txs = AI_CLASSIFIER.batch_classify(transactions)
            extracted_data["ai_enriched_transactions"] = ai_enriched_txs

            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)

            subprocess.run(trans_cmd, capture_output=True, text=True, check=True)

            # 3. QEMU Windows 11 VM Import (Delta Pro & SQLEXPRESS)
            subprocess.run(vm_cmd, capture_output=True, text=True, check=True)

            # 4. Audit Log Export
            subprocess.run(audit_cmd, capture_output=True, text=True, check=True)

            # 5. Obsidian Vault Note Sync
            obsidian_note = OBSIDIAN_EXPORTER.export_statement_note(
                extracted_json_path=json_out,
                journal_json_path=journal_out,
                audit_log_path=audit_out,
                pdf_name=os.path.basename(pdf_path)
            )

            # 6. Supabase Database Logging
            telemetry_event = TELEMETRY_CLIENT.build_event(
                json_path=json_out,
                audit_log_path=audit_out,
                pdf_path=pdf_path,
                status="SUCCESS"
            )
            SUPABASE_LOGGER.log_statement_run(extracted_data, status="SUCCESS", audit_sha256=telemetry_event.audit_checksum_sha256)

            # 7. OpenBalancer Dashboard Telemetry Emission
            TELEMETRY_CLIENT.send_telemetry(telemetry_event)

            res_payload = {
                "status": "SUCCESS",
                "message": "Microinvest Bank Statement OCR & Delta Pro Import Completed Successfully with Full Self-Hosted Ecosystem Integration",
                "extracted_count": telemetry_event.extracted_count,
                "discrepancy": f"{telemetry_event.balance_discrepancy:.2f} EUR",
                "pdf_processed": pdf_path,
                "transfer_xml": xml_out,
                "journal_json": journal_out,
                "audit_log": audit_out,
                "obsidian_note": obsidian_note,
                "infisical_vault": "CONNECTED",
                "unsloth_ai_model": AI_CLASSIFIER.model_name,
                "supabase_database": "LOGGED",
                "openbalancer_telemetry": {
                    "pipeline_id": telemetry_event.pipeline_id,
                    "audit_sha256": telemetry_event.audit_checksum_sha256,
                    "dashboard_url": "https://n8n.openbalancer.com",
                    "status": telemetry_event.status
                },
                "steps": [
                    "INFISICAL_SECRETS_LOADED",
                    "PDF_OCR_EXTRACTED",
                    "UNSLOTH_AI_CLASSIFIED",
                    "ACCOUNTING_TRANSLATED",
                    "QEMU_VM_VNC_SQL_IMPORTED",
                    "TRANSFER_LOG_AUDITED",
                    "OBSIDIAN_NOTE_SYNCD",
                    "SUPABASE_LOGGED",
                    "OPENBALANCER_TELEMETRY_EMITTED"
                ]
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res_payload, indent=2, ensure_ascii=False).encode("utf-8"))

        except subprocess.CalledProcessError as exc:
            err_payload = {
                "status": "ERROR",
                "message": f"Pipeline failed: {exc}",
                "stderr": exc.stderr,
                "stdout": exc.stdout
            }
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(err_payload, indent=2, ensure_ascii=False).encode("utf-8"))


def main():
    server = http.server.HTTPServer(("0.0.0.0", PORT), StatementHandler)
    print(f"🚀 Microinvest OCR Full Ecosystem Service running on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down service.")
        server.server_close()


if __name__ == "__main__":
    main()
