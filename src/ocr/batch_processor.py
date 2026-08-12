"""
Multi-PDF Batch Processing Queue Module.

Supports scanning directories for bank statement PDFs, extracting ZIP archives containing
multiple statement files, processing them in parallel or sequentially with fault tolerance,
and aggregating transactions, double-entry accounting journals, and audit metrics.
"""

import dataclasses
import json
import logging
import os
import shutil
import tempfile
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from src.ocr.extract_dsk_statement import DSKStatementExtractor

logger = logging.getLogger("batch_processor")


@dataclasses.dataclass
class SingleFileResult:
    """Result container for a single statement file processing attempt."""

    filepath: str
    status: str  # "SUCCESS" | "ERROR"
    transaction_count: int
    total_debits: float
    total_credits: float
    opening_balance: float
    closing_balance: float
    error_message: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None


@dataclasses.dataclass
class BatchProcessingResult:
    """Consolidated result container for a multi-PDF batch run."""

    batch_id: str
    total_files: int
    successful_files: int
    failed_files: int
    total_transactions: int
    grand_total_debits: float
    grand_total_credits: float
    file_results: List[SingleFileResult]
    consolidated_transactions: List[Dict[str, Any]]
    consolidated_metadata: Dict[str, Any]


class MultiPDFBatchProcessor:
    """Batch Processor for handling multi-PDF bank statement queues and ZIP archives."""

    def __init__(self, temp_work_dir: Optional[str] = None):
        self.temp_work_dir = temp_work_dir or tempfile.gettempdir()

    @staticmethod
    def scan_directory_for_pdfs(dir_path: str) -> List[str]:
        """Scans a target directory for all PDF files (case-insensitive extension)."""
        if not os.path.exists(dir_path):
            logger.error(f"Target directory does not exist: {dir_path}")
            return []

        pdf_files = []
        for root, _, files in os.walk(dir_path):
            for file in sorted(files):
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
        logger.info(f"Found {len(pdf_files)} PDF statement files in {dir_path}")
        return pdf_files

    def extract_zip_archive(self, zip_path: str, extract_to: Optional[str] = None) -> List[str]:
        """Extracts a ZIP archive containing PDF statement files to a target directory."""
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP archive not found: {zip_path}")

        target_dir = extract_to or os.path.join(self.temp_work_dir, f"zip_extract_{os.path.basename(zip_path)}")
        os.makedirs(target_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)

        pdf_files = self.scan_directory_for_pdfs(target_dir)
        logger.info(f"Extracted {len(pdf_files)} PDF files from ZIP archive '{zip_path}' to '{target_dir}'")
        return pdf_files

    def process_single_pdf(self, pdf_path: str) -> SingleFileResult:
        """Processes a single PDF statement file with error boundary isolations."""
        if not os.path.exists(pdf_path):
            return SingleFileResult(
                filepath=pdf_path,
                status="ERROR",
                transaction_count=0,
                total_debits=0.0,
                total_credits=0.0,
                opening_balance=0.0,
                closing_balance=0.0,
                error_message=f"File not found: {pdf_path}",
            )

        try:
            extractor = DSKStatementExtractor(pdf_path=pdf_path, strict=False)
            dataset = extractor.extract_and_build_dataset()

            meta = dataset.get("statement_metadata", {})
            txs = dataset.get("transactions", [])

            tx_count = len(txs)
            opening_bal = float(meta.get("opening_balance", 0.0))
            debits = sum(float(t.get("debit_amount", 0.0)) for t in txs)
            credits = sum(float(t.get("credit_amount", 0.0)) for t in txs)
            closing_bal = opening_bal - debits + credits

            return SingleFileResult(
                filepath=pdf_path,
                status="SUCCESS",
                transaction_count=tx_count,
                total_debits=round(debits, 2),
                total_credits=round(credits, 2),
                opening_balance=round(opening_bal, 2),
                closing_balance=round(closing_bal, 2),
                extracted_data=dataset,
            )
        except Exception as e:
            logger.error(f"Error processing PDF '{pdf_path}': {e}")
            return SingleFileResult(
                filepath=pdf_path,
                status="ERROR",
                transaction_count=0,
                total_debits=0.0,
                total_credits=0.0,
                opening_balance=0.0,
                closing_balance=0.0,
                error_message=str(e),
            )

    def process_batch(
        self, pdf_paths: List[str], batch_id: Optional[str] = None
    ) -> BatchProcessingResult:
        """Processes a batch queue of PDF statement filepaths and returns consolidated metrics."""
        b_id = batch_id or f"batch_{int(os.getpid())}"
        file_results: List[SingleFileResult] = []
        consolidated_txs: List[Dict[str, Any]] = []

        total_debits = 0.0
        total_credits = 0.0
        successful_count = 0
        failed_count = 0

        first_meta: Dict[str, Any] = {}

        for path in pdf_paths:
            res = self.process_single_pdf(path)
            file_results.append(res)

            if res.status == "SUCCESS" and res.extracted_data:
                successful_count += 1
                total_debits += res.total_debits
                total_credits += res.total_credits

                if not first_meta:
                    first_meta = res.extracted_data.get("statement_metadata", {})

                # Tag each transaction with source file for traceability
                txs = res.extracted_data.get("transactions", [])
                for t in txs:
                    t_copy = dict(t)
                    t_copy["source_pdf"] = os.path.basename(path)
                    consolidated_txs.append(t_copy)
            else:
                failed_count += 1

        batch_result = BatchProcessingResult(
            batch_id=b_id,
            total_files=len(pdf_paths),
            successful_files=successful_count,
            failed_files=failed_count,
            total_transactions=len(consolidated_txs),
            grand_total_debits=round(total_debits, 2),
            grand_total_credits=round(total_credits, 2),
            file_results=file_results,
            consolidated_transactions=consolidated_txs,
            consolidated_metadata=first_meta,
        )

        logger.info(
            f"Batch {b_id} completed: {successful_count}/{len(pdf_paths)} successful files, "
            f"{len(consolidated_txs)} total transactions, €{total_debits:.2f} debits, €{total_credits:.2f} credits."
        )
        return batch_result
