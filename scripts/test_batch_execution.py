#!/usr/bin/env python3
"""
Real-world Multi-PDF Batch Queue Verification Script.
Executes batch ingestion on 3 real-world DSK bank statement PDFs:
1.pdf, 2.pdf, 4.pdf
"""

import json
import os
import sys

# Ensure workspace root is in python path
work_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if work_dir not in sys.path:
    sys.path.insert(0, work_dir)

from src.ocr.batch_processor import MultiPDFBatchProcessor

def main():
    scan_dir = "/Volumes/KINGSTON/Persist/Scans/Storgozia AD/DSK_01-06"
    processor = MultiPDFBatchProcessor()

    pdf_files = processor.scan_directory_for_pdfs(scan_dir)
    print(f"🔍 Discovered {len(pdf_files)} PDF statement files in {scan_dir}")

    # Process first 3 PDFs in real-world batch queue
    target_pdfs = pdf_files[:3]
    print(f"🚀 Processing real-world batch queue on files: {[os.path.basename(p) for p in target_pdfs]}")

    batch_result = processor.process_batch(target_pdfs, batch_id="rw_batch_001")

    print("\n==================================================")
    print(f"✅ BATCH EXECUTION COMPLETED: {batch_result.batch_id}")
    print(f"• Total Files Processed: {batch_result.total_files}")
    print(f"• Successful Files: {batch_result.successful_files}")
    print(f"• Failed Files: {batch_result.failed_files}")
    print(f"• Total Extracted Transactions: {batch_result.total_transactions}")
    print(f"• Grand Total Debits: €{batch_result.grand_total_debits:,.2f}")
    print(f"• Grand Total Credits: €{batch_result.grand_total_credits:,.2f}")
    print("==================================================")

    for res in batch_result.file_results:
        print(f"  📄 [{res.status}] {os.path.basename(res.filepath)}: {res.transaction_count} txs | Debits: €{res.total_debits:.2f} | Credits: €{res.total_credits:.2f}")

if __name__ == "__main__":
    main()
