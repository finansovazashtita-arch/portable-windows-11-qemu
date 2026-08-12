#!/usr/bin/env python3
"""
Microinvest Bank Statement OCR & Delta Pro Automation Service for n8n Integration
with OpenBalancer Dashboard & FinansProtect Telemetry Reporting.

Listens on HTTP port 8090 (0.0.0.0:8090) and executes end-to-end processing pipeline.
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

from src.dashboard.openbalancer_client import OpenBalancerClient

PORT = 8090
DEFAULT_PDF = f"{WORK_DIR}/data/1.pdf"
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

        # Execute Pipeline Steps
        ocr_cmd = [python_bin, f"{WORK_DIR}/src/ocr/extract_dsk_statement.py", "--pdf-path", pdf_path, "--output", json_out]
        trans_cmd = [python_bin, f"{WORK_DIR}/src/accounting/translate_to_delta.py", "--input", json_out, "--output-dir", "/tmp"]
        vm_cmd = [python_bin, f"{WORK_DIR}/src/vm_automation/import_to_deltapro.py", "--xml", xml_out]
        audit_cmd = [python_bin, f"{WORK_DIR}/src/audit/generate_transfer_log.py", "--json-path", journal_out, "--output-path", audit_out]

        try:
            subprocess.run(ocr_cmd, capture_output=True, text=True, check=True)
            subprocess.run(trans_cmd, capture_output=True, text=True, check=True)
            subprocess.run(vm_cmd, capture_output=True, text=True, check=True)
            subprocess.run(audit_cmd, capture_output=True, text=True, check=True)

            # Emit OpenBalancer & FinansProtect Telemetry
            telemetry_event = TELEMETRY_CLIENT.build_event(
                json_path=json_out,
                audit_log_path=audit_out,
                pdf_path=pdf_path,
                status="SUCCESS"
            )
            TELEMETRY_CLIENT.send_telemetry(telemetry_event)

            res_payload = {
                "status": "SUCCESS",
                "message": "Microinvest Bank Statement OCR & Delta Pro Import Completed Successfully via n8n",
                "extracted_count": telemetry_event.extracted_count,
                "discrepancy": f"{telemetry_event.balance_discrepancy:.2f} EUR",
                "pdf_processed": pdf_path,
                "transfer_xml": xml_out,
                "journal_json": journal_out,
                "audit_log": audit_out,
                "openbalancer_telemetry": {
                    "pipeline_id": telemetry_event.pipeline_id,
                    "audit_sha256": telemetry_event.audit_checksum_sha256,
                    "dashboard_url": "https://n8n.openbalancer.com",
                    "status": telemetry_event.status
                },
                "steps": ["OCR_EXTRACTED", "ACCOUNTING_TRANSLATED", "VNC_SQL_IMPORTED", "TRANSFER_LOG_WRITTEN"]
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
    print(f"🚀 Microinvest OCR n8n & OpenBalancer Service running on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down service.")
        server.server_close()


if __name__ == "__main__":
    main()
