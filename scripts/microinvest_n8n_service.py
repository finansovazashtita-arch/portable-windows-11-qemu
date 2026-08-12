#!/usr/bin/env python3
"""
Microinvest Bank Statement OCR & Delta Pro Automation Service with Multi-PDF Batch Processing
and Full Infrastructure Integration:
- Multi-PDF Batch Queue & ZIP Archive Processing
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
from src.ocr.batch_processor import MultiPDFBatchProcessor
from src.security.infisical_vault import InfisicalVaultClient

PORT = 8090
DEFAULT_PDF = f"{WORK_DIR}/data/1.pdf"

# Initialize Infrastructure Clients
VAULT_CLIENT = InfisicalVaultClient()
AI_CLASSIFIER = UnslothTransactionClassifier()
OBSIDIAN_EXPORTER = ObsidianVaultExporter()
SUPABASE_LOGGER = SupabaseLogger()
TELEMETRY_CLIENT = OpenBalancerClient()
BATCH_PROCESSOR = MultiPDFBatchProcessor()


class StatementHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        path = self.path.split("?")[0]

        if path == "/process-batch":
            self.handle_batch_request(payload)
        else:
            self.handle_single_statement_request(payload)

    def handle_batch_request(self, payload: Dict[str, Any]):
        pdf_paths = payload.get("pdf_paths", [])
        dir_path = payload.get("dir_path")
        zip_path = payload.get("zip_path")

        if zip_path and os.path.exists(zip_path):
            extracted = BATCH_PROCESSOR.extract_zip_archive(zip_path)
            pdf_paths.extend(extracted)
        elif dir_path and os.path.exists(dir_path):
            scanned = BATCH_PROCESSOR.scan_directory_for_pdfs(dir_path)
            pdf_paths.extend(scanned)

        if not pdf_paths:
            pdf_paths = [DEFAULT_PDF]

        batch_result = BATCH_PROCESSOR.process_batch(pdf_paths)

        json_out = "/tmp/extracted_transactions.json"
        xml_out = "/tmp/microinvest_transferdata.xml"
        journal_out = "/tmp/journal_entries.json"
        audit_out = "/tmp/TRANSFER.LOG"

        # Save consolidated JSON
        consolidated_payload = {
            "statement_metadata": batch_result.consolidated_metadata,
            "transactions": batch_result.consolidated_transactions,
            "batch_summary": {
                "batch_id": batch_result.batch_id,
                "total_files": batch_result.total_files,
                "successful_files": batch_result.successful_files,
                "failed_files": batch_result.failed_files,
                "grand_total_debits": batch_result.grand_total_debits,
                "grand_total_credits": batch_result.grand_total_credits,
            },
        }

        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(consolidated_payload, f, indent=2, ensure_ascii=False)

        python_bin = sys.executable
        trans_cmd = [python_bin, f"{WORK_DIR}/src/accounting/translate_to_delta.py", "--input", json_out, "--output-dir", "/tmp"]
        vm_cmd = [python_bin, f"{WORK_DIR}/src/vm_automation/import_to_deltapro.py", "--xml", xml_out]
        audit_cmd = [python_bin, f"{WORK_DIR}/src/audit/generate_transfer_log.py", "--json-path", journal_out, "--output-path", audit_out]

        try:
            subprocess.run(trans_cmd, capture_output=True, text=True, check=True)
            subprocess.run(vm_cmd, capture_output=True, text=True, check=True)
            subprocess.run(audit_cmd, capture_output=True, text=True, check=True)

            obsidian_note = OBSIDIAN_EXPORTER.export_statement_note(
                extracted_json_path=json_out,
                journal_json_path=journal_out,
                audit_log_path=audit_out,
                pdf_name=f"Batch_{batch_result.batch_id}.pdf"
            )

            telemetry_event = TELEMETRY_CLIENT.build_event(
                json_path=json_out,
                audit_log_path=audit_out,
                pdf_path=f"batch_{batch_result.batch_id}",
                status="SUCCESS"
            )
            SUPABASE_LOGGER.log_statement_run(consolidated_payload, status="SUCCESS", audit_sha256=telemetry_event.audit_checksum_sha256)
            TELEMETRY_CLIENT.send_telemetry(telemetry_event)

            res_payload = {
                "status": "SUCCESS",
                "message": f"Multi-PDF Batch Processing Completed: {batch_result.successful_files}/{batch_result.total_files} files processed successfully",
                "batch_id": batch_result.batch_id,
                "total_files": batch_result.total_files,
                "successful_files": batch_result.successful_files,
                "failed_files": batch_result.failed_files,
                "total_transactions": batch_result.total_transactions,
                "grand_total_debits": f"{batch_result.grand_total_debits:.2f} EUR",
                "grand_total_credits": f"{batch_result.grand_total_credits:.2f} EUR",
                "obsidian_note": obsidian_note,
                "steps": [
                    "MULTI_PDF_BATCH_INGESTED",
                    "PARALLEL_OCR_EXTRACTED",
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
        except Exception as exc:
            err_payload = {"status": "ERROR", "message": f"Batch pipeline error: {exc}"}
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(err_payload, indent=2, ensure_ascii=False).encode("utf-8"))

    def handle_single_statement_request(self, payload: Dict[str, Any]):
        pdf_path = payload.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            pdf_path = DEFAULT_PDF

        python_bin = sys.executable
        json_out = "/tmp/extracted_transactions.json"
        xml_out = "/tmp/microinvest_transferdata.xml"
        journal_out = "/tmp/journal_entries.json"
        audit_out = "/tmp/TRANSFER.LOG"

        ocr_cmd = [python_bin, f"{WORK_DIR}/src/ocr/extract_dsk_statement.py", "--pdf-path", pdf_path, "--output", json_out]
        trans_cmd = [python_bin, f"{WORK_DIR}/src/accounting/translate_to_delta.py", "--input", json_out, "--output-dir", "/tmp"]
        vm_cmd = [python_bin, f"{WORK_DIR}/src/vm_automation/import_to_deltapro.py", "--xml", xml_out]
        audit_cmd = [python_bin, f"{WORK_DIR}/src/audit/generate_transfer_log.py", "--json-path", journal_out, "--output-path", audit_out]

        try:
            subprocess.run(ocr_cmd, capture_output=True, text=True, check=True)

            with open(json_out, "r", encoding="utf-8") as f:
                extracted_data = json.load(f)

            transactions = extracted_data.get("transactions", [])
            extracted_data["ai_enriched_transactions"] = AI_CLASSIFIER.batch_classify(transactions)

            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)

            subprocess.run(trans_cmd, capture_output=True, text=True, check=True)
            subprocess.run(vm_cmd, capture_output=True, text=True, check=True)
            subprocess.run(audit_cmd, capture_output=True, text=True, check=True)

            obsidian_note = OBSIDIAN_EXPORTER.export_statement_note(
                extracted_json_path=json_out,
                journal_json_path=journal_out,
                audit_log_path=audit_out,
                pdf_name=os.path.basename(pdf_path)
            )

            telemetry_event = TELEMETRY_CLIENT.build_event(
                json_path=json_out,
                audit_log_path=audit_out,
                pdf_path=pdf_path,
                status="SUCCESS"
            )
            SUPABASE_LOGGER.log_statement_run(extracted_data, status="SUCCESS", audit_sha256=telemetry_event.audit_checksum_sha256)
            TELEMETRY_CLIENT.send_telemetry(telemetry_event)

            res_payload = {
                "status": "SUCCESS",
                "message": "Microinvest Bank Statement OCR & Delta Pro Import Completed Successfully",
                "extracted_count": telemetry_event.extracted_count,
                "discrepancy": f"{telemetry_event.balance_discrepancy:.2f} EUR",
                "pdf_processed": pdf_path,
                "transfer_xml": xml_out,
                "journal_json": journal_out,
                "audit_log": audit_out,
                "obsidian_note": obsidian_note,
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
        except Exception as exc:
            err_payload = {"status": "ERROR", "message": f"Pipeline failed: {exc}"}
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(err_payload, indent=2, ensure_ascii=False).encode("utf-8"))


def main():
    server = http.server.HTTPServer(("0.0.0.0", PORT), StatementHandler)
    print(f"🚀 Microinvest OCR Batch & Ecosystem Service running on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down service.")
        server.server_close()


if __name__ == "__main__":
    main()
