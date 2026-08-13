"""
Multi-Modal Document Reconciliation Engine.

Performs 3-way cross-reconciliation between:
- PDF Invoices
- Scanned Paper Receipts (Фискални бонове)
- Bank Statement Transactions
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("multimodal_reconciler")


class DocumentType(str, enum.Enum):
    INVOICE = "INVOICE"
    CASH_RECEIPT = "CASH_RECEIPT"
    BANK_STATEMENT = "BANK_STATEMENT"


class ReconciliationStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    DISCREPANCY = "DISCREPANCY"
    UNMATCHED = "UNMATCHED"


@dataclasses.dataclass
class ReconciliationMatch:
    """Dataclass holding outcome of 3-way document reconciliation."""

    invoice_id: str
    receipt_id: str
    bank_tx_id: str
    match_confidence: float
    amount_difference: float
    status: ReconciliationStatus
    notes: str


ReconciliationMatchResult = ReconciliationMatch


class MultiModalReconciler:
    """3-Way Cross-Document Reconciler (Invoices ↔ Receipts ↔ Bank Transactions)."""

    @classmethod
    def reconcile_3way(
        cls,
        invoices: List[Dict[str, Any]],
        receipts: List[Dict[str, Any]],
        bank_txs: List[Dict[str, Any]],
    ) -> List[ReconciliationMatch]:
        """Performs 3-way cross-matching across document lists."""
        matches = []

        for inv in invoices:
            inv_no = str(inv.get("doc_number", "N/A"))
            inv_amt = float(inv.get("amount", 0.0))

            # 1. Match against Bank Transactions (Exact match first, then M71 Smart AI Matcher)
            matched_tx = None
            tx_confidence = 0.99
            tx_notes = ""
            for tx in bank_txs:
                tx_amt = float(tx.get("debit_amount", 0.0)) or float(tx.get("credit_amount", 0.0))
                if abs(tx_amt - inv_amt) < 0.01:
                    matched_tx = tx
                    tx_confidence = 0.99
                    break

            if not matched_tx and bank_txs:
                try:
                    from src.ai.smart_invoice_matcher import SmartInvoiceMatcher
                    ai_candidates = SmartInvoiceMatcher.match_invoices_and_bank_txs([inv], bank_txs, min_confidence_threshold=0.5)
                    if ai_candidates:
                        best = ai_candidates[0]
                        matched_tx = next((t for t in bank_txs if str(t.get("item_id", "")) == best.bank_tx_id), None)
                        tx_confidence = best.overall_confidence
                        tx_notes = f" (M71 AI Similarity Score: {round(best.overall_confidence*100, 1)}%)"
                except Exception as e:
                    logger.debug(f"Smart AI invoice matcher fallback error: {e}")

            # 2. Match against Receipts
            matched_receipt = None
            for rec in receipts:
                rec_amt = float(rec.get("amount", 0.0))
                if abs(rec_amt - inv_amt) < 0.01:
                    matched_receipt = rec
                    break

            if matched_tx and matched_receipt:
                matches.append(
                    ReconciliationMatch(
                        invoice_id=inv_no,
                        receipt_id=str(matched_receipt.get("receipt_id", "REC_01")),
                        bank_tx_id=str(matched_tx.get("item_id", "TX_01")),
                        match_confidence=tx_confidence,
                        amount_difference=0.0,
                        status=ReconciliationStatus.MATCHED,
                        notes=f"Идеална 3-странна съвместимост между фактура, бон и банка.{tx_notes}",
                    )
                )
            elif matched_tx:
                matches.append(
                    ReconciliationMatch(
                        invoice_id=inv_no,
                        receipt_id="MISSING",
                        bank_tx_id=str(matched_tx.get("item_id", "TX_01")),
                        match_confidence=tx_confidence,
                        amount_difference=0.0,
                        status=ReconciliationStatus.MATCHED,
                        notes=f"Фактурата и банката съвпадат (липсва хартиен касов бон).{tx_notes}",
                    )
                )
            else:
                matches.append(
                    ReconciliationMatch(
                        invoice_id=inv_no,
                        receipt_id="MISSING",
                        bank_tx_id="MISSING",
                        match_confidence=0.0,
                        amount_difference=inv_amt,
                        status=ReconciliationStatus.UNMATCHED,
                        notes="Не са открити банкови плащания за тази фактура.",
                    )
                )

        logger.info(f"Reconciled {len(invoices)} invoices across receipts and bank transactions.")
        return matches
