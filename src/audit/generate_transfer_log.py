"""SQL Verification & TRANSFER.LOG Exporter Module for Microinvest Delta Pro.

Implements 3-way reconciliation (PDF OCR ↔ Journal Entries ↔ SQLEXPRESS DB Records),
persistent audit log generation (C:\\TRANSFER.LOG), and compliance auditing.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union


def _sql_escape(val: Any) -> str:
    """Escapes single quotes for T-SQL literals."""
    if val is None:
        return ""
    return str(val).replace("'", "''")


def _extract_tx_list(payload: Union[List[Dict[str, Any]], Dict[str, Any], None]) -> List[Dict[str, Any]]:
    """Helper to extract transaction list from either direct list or dict wrapper payload."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("transactions", "journal_entries", "records", "data"):
            val = payload.get(key)
            if isinstance(val, list):
                return [item for item in val if isinstance(item, dict)]
    return []


def _get_item_amount(item: Dict[str, Any]) -> float:
    """Safely extracts total monetary amount for a transaction item."""
    if not isinstance(item, dict):
        return 0.0
    if "debit_amount" in item or "credit_amount" in item:
        try:
            return float(item.get("debit_amount") or 0.0) + float(item.get("credit_amount") or 0.0)
        except (ValueError, TypeError, OverflowError):
            return 0.0
    raw_amt = item.get("amount", item.get("Amount", item.get("TotalEUR", 0.0)))
    try:
        return float(raw_amt) if raw_amt is not None else 0.0
    except (ValueError, TypeError, OverflowError):
        return 0.0


def _get_item_doc(item: Dict[str, Any]) -> str:
    """Safely extracts document number string for a transaction item."""
    if not isinstance(item, dict):
        return ""
    for key in ("doc_no", "DocNum", "DocumentNumber", "document_number"):
        if key in item and item[key] is not None:
            return str(item[key]).strip()
    return ""


def reconcile_3way(
    extracted_transactions: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    journal_entries: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    sql_records: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Performs 3-way reconciliation across OCR extractions, double-entry journal entries,
    and MS SQL database records.
    
    Returns reconciliation summary including status ('MATCHED', 'PARTIAL', or 'UNMATCHED'),
    matched record counts, amount totals, and any discrepancy details.
    """
    discrepancies: List[str] = []

    ocr_txs = _extract_tx_list(extracted_transactions)
    journal_txs = _extract_tx_list(journal_entries)
    sql_txs = _extract_tx_list(sql_records)

    ocr_count = len(ocr_txs)
    journal_count = len(journal_txs)
    sql_count = len(sql_txs)

    # Track missing / empty datasets
    missing_sources = []
    if extracted_transactions is None or ocr_count == 0:
        missing_sources.append("OCR")
    if journal_entries is None or journal_count == 0:
        missing_sources.append("Journal")
    if sql_records is None or sql_count == 0:
        missing_sources.append("SQL")

    if missing_sources:
        discrepancies.append(f"Missing source dataset(s): {', '.join(missing_sources)}")

    # Count check across all PROVIDED datasets (parameters that are not None)
    provided_counts = []
    if extracted_transactions is not None:
        provided_counts.append(ocr_count)
    if journal_entries is not None:
        provided_counts.append(journal_count)
    if sql_records is not None:
        provided_counts.append(sql_count)

    if provided_counts and len(set(provided_counts)) > 1:
        discrepancies.append(
            f"Record count mismatch: OCR={ocr_count}, Journal={journal_count}, SQL={sql_count}"
        )

    # Amount totals reconciliation
    ocr_sum = sum(_get_item_amount(t) for t in ocr_txs)
    journal_sum = sum(_get_item_amount(t) for t in journal_txs)
    sql_sum = sum(_get_item_amount(t) for t in sql_txs)

    ocr_total = round(ocr_sum, 2)
    journal_total = round(journal_sum, 2)
    sql_total = round(sql_sum, 2)

    present_totals = [t for count, t in ((ocr_count, ocr_sum), (journal_count, journal_sum), (sql_count, sql_sum)) if count > 0]
    if len(present_totals) > 1:
        # Check pairwise floating point difference with < 0.001 tolerance
        for i in range(len(present_totals)):
            for j in range(i + 1, len(present_totals)):
                if abs(present_totals[i] - present_totals[j]) >= 0.001:
                    discrepancies.append(
                        f"Total amount mismatch: OCR={ocr_total:.2f}, Journal={journal_total:.2f}, SQL={sql_total:.2f}"
                    )
                    break
            else:
                continue
            break

    # Line-item level matching (Document Number & Amount)
    present_sources = []
    if ocr_count > 0:
        present_sources.append(("OCR", ocr_txs))
    if journal_count > 0:
        present_sources.append(("Journal", journal_txs))
    if sql_count > 0:
        present_sources.append(("SQL", sql_txs))

    present_counts = [c for c in (ocr_count, journal_count, sql_count) if c > 0]
    if len(present_sources) >= 2 and len(set(present_counts)) == 1:
        min_len = present_counts[0]
        for idx in range(min_len):
            # Line item document numbers check
            docs = {sname: _get_item_doc(stxs[idx]) for sname, stxs in present_sources}
            non_empty_docs = {name: d for name, d in docs.items() if d}
            if len(set(non_empty_docs.values())) > 1:
                details = ", ".join(f"{name}='{d}'" for name, d in docs.items())
                discrepancies.append(f"Line item {idx + 1} document number mismatch: {details}")

            # Line item amount check (rounded to 2 decimal places prior to comparison)
            amts = {sname: round(_get_item_amount(stxs[idx]), 2) for sname, stxs in present_sources}
            amt_vals = list(amts.values())
            for i in range(len(amt_vals)):
                for j in range(i + 1, len(amt_vals)):
                    if abs(amt_vals[i] - amt_vals[j]) >= 0.001:
                        details = ", ".join(f"{name}={a:.2f}" for name, a in amts.items())
                        discrepancies.append(f"Line item {idx + 1} amount mismatch: {details}")
                        break
                else:
                    continue
                break

    reconciled_count = max(ocr_count, journal_count, sql_count)

    # Determine status
    if len(missing_sources) == 0 and not discrepancies:
        status = "MATCHED"
    elif len(present_sources) > 0 and not any(
        "mismatch" in d.lower() for d in discrepancies
    ):
        status = "PARTIAL"
    else:
        status = "UNMATCHED"

    return {
        "reconciliation_status": status,
        "reconciled_count": reconciled_count,
        "ocr_count": ocr_count,
        "journal_count": journal_count,
        "sql_count": sql_count,
        "ocr_total_eur": ocr_total,
        "journal_total_eur": journal_total,
        "sql_total_eur": sql_total,
        "discrepancies": discrepancies,
    }


def generate_transfer_log(
    sql_records: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    journal_entries: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    target_path: Optional[str] = None,
    extracted_transactions: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generates guest audit log C:\\TRANSFER.LOG and performs 3-way reconciliation.

    Main entrypoint for audit log export.
    """
    raw_entries = journal_entries or sql_records or extracted_transactions or []
    entries = _extract_tx_list(raw_entries)

    if not entries and os.path.exists("data/journal_entries.json"):
        try:
            with open("data/journal_entries.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                entries = _extract_tx_list(data)
        except Exception:
            entries = []

    dest_path = target_path or r"C:\TRANSFER.LOG"

    # Normalize entries to list of dicts with required audit fields
    norm_records: List[Dict[str, Any]] = []
    for idx, raw in enumerate(entries, 1):
        if not isinstance(raw, dict):
            continue

        item_no = raw.get("item_id", raw.get("ItemNo", raw.get("OpID", idx)))
        if item_no is None:
            item_no = idx

        raw_date = None
        for key in ("posting_date", "PostingDate", "Date", "OpDate"):
            if key in raw and raw[key] is not None:
                raw_date = raw[key]
                break
        date = str(raw_date).strip() if raw_date is not None else ""

        doc_val = None
        for key in ("doc_no", "DocNum", "DocumentNumber", "document_number"):
            if key in raw and raw[key] is not None:
                doc_val = raw[key]
                break
        doc_num = str(doc_val).strip() if doc_val is not None else ""

        raw_cp = None
        for key in ("counterparty_name", "Counterparty", "CounterpartyName", "Company"):
            if key in raw and raw[key] is not None:
                raw_cp = raw[key]
                break
        counterparty = str(raw_cp).strip() if raw_cp is not None else ""

        eik_val = None
        for key in ("counterparty_eik", "CounterpartyEIK", "CompanyEIK", "EIK"):
            if key in raw and raw[key] is not None and str(raw[key]).strip():
                eik_val = str(raw[key]).strip()
                break
        counterparty_eik = eik_val if eik_val else "114077876"

        raw_debit = None
        for key in ("debit_account", "DebitAcc", "DebitAccount", "DebitAcct"):
            if key in raw and raw[key] is not None:
                raw_debit = raw[key]
                break
        debit_acc = str(raw_debit).strip() if raw_debit is not None else ""

        raw_credit = None
        for key in ("credit_account", "CreditAcc", "CreditAccount", "CreditAcct"):
            if key in raw and raw[key] is not None:
                raw_credit = raw[key]
                break
        credit_acc = str(raw_credit).strip() if raw_credit is not None else ""

        amt = _get_item_amount(raw)

        raw_curr = None
        for key in ("currency", "Currency"):
            if key in raw and raw[key] is not None and str(raw[key]).strip():
                raw_curr = str(raw[key]).strip()
                break
        currency = raw_curr if raw_curr else "EUR"

        # Deduplication hash extraction & fallback generation
        hash_val = None
        for key in ("dedup_hash", "sha256_hash", "DedupHash", "Hash"):
            if key in raw and raw[key] is not None and str(raw[key]).strip():
                hash_val = str(raw[key]).strip()
                break

        if hash_val:
            dedup_hash = hash_val
        else:
            hash_input = f"{counterparty_eik}|{doc_num}|{amt:.2f}"
            dedup_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        norm_records.append({
            "ItemNo": item_no,
            "Date": date,
            "DocNum": doc_num,
            "Counterparty": counterparty,
            "CounterpartyEIK": counterparty_eik,
            "DebitAcc": debit_acc,
            "CreditAcc": credit_acc,
            "Amount": amt,
            "Currency": currency,
            "DedupHash": dedup_hash,
        })

    # Format log content
    log_lines = [
        "# MICROINVEST DELTA PRO TRANSFER AUDIT LOG",
        f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "# Format: ItemNo|Date|DocNum|Counterparty|DebitAcc|CreditAcc|Amount|Currency|DedupHash",
    ]

    for r in norm_records:
        line = f"{r['ItemNo']}|{r['Date']}|{r['DocNum']}|{r['Counterparty']}|{r['DebitAcc']}|{r['CreditAcc']}|{r['Amount']:.2f}|{r['Currency']}|{r['DedupHash']}"
        log_lines.append(line)

    log_content = "\n".join(log_lines) + "\n"

    # Cross-platform path handling for C:\TRANSFER.LOG
    actual_path = dest_path
    if os.name != "nt":
        if len(dest_path) >= 2 and dest_path[1] == ":" and dest_path[0].isalpha():
            actual_path = "/tmp/TRANSFER.LOG"

    try:
        dir_name = os.path.dirname(os.path.abspath(actual_path))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(actual_path, "w", encoding="utf-8") as f:
            f.write(log_content)
    except Exception:
        actual_path = "/tmp/TRANSFER.LOG"
        with open(actual_path, "w", encoding="utf-8") as f:
            f.write(log_content)

    reconciliation = reconcile_3way(extracted_transactions, journal_entries, sql_records)

    return {
        "log_path": actual_path,
        "target_path": dest_path,
        "log_content": log_content,
        "count": len(norm_records),
        "reconciliation": reconciliation,
        "reconciliation_status": reconciliation["reconciliation_status"],
        "records": norm_records,
        "status": "SUCCESS",
    }


def export_audit_log(
    sql_records: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    journal_entries: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    target_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Alias function for audit log exporter."""
    return generate_transfer_log(sql_records=sql_records, journal_entries=journal_entries, target_path=target_path)


def run_audit_export(
    sql_records: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    journal_entries: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    target_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Fixture hook alias function for audit log exporter."""
    return generate_transfer_log(sql_records=sql_records, journal_entries=journal_entries, target_path=target_path)


def main() -> None:
    """CLI entrypoint for generate_transfer_log."""
    parser = argparse.ArgumentParser(description="Microinvest Delta Pro TRANSFER.LOG Audit Exporter")
    parser.add_argument("--json-path", help="Path to journal_entries.json")
    parser.add_argument("--output-path", default=r"C:\TRANSFER.LOG", help="Output path for TRANSFER.LOG")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    journal_entries = None
    if args.json_path and os.path.exists(args.json_path):
        with open(args.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            journal_entries = _extract_tx_list(data)

    result = generate_transfer_log(journal_entries=journal_entries, target_path=args.output_path)
    print(json.dumps({
        "status": result["status"],
        "log_path": result["log_path"],
        "count": result["count"],
        "reconciliation_status": result["reconciliation_status"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

