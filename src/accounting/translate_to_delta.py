"""Bulgarian Double-Entry Accounting Translation Engine for Microinvest Delta Pro.

Translates extracted bank statement transactions (canonical JSON) into Bulgarian
double-entry accounting journal records, Microinvest TransferData XML (`urn:Transfer`),
and Delta BG CSV format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple


def validate_eik(eik: str) -> bool:
    """Validates Bulgarian EIK 9-digit or 13-digit checksum using Modulo 11 algorithm.

    Args:
        eik: 9 or 13 digit string representation of EIK/BULSTAT.

    Returns:
        True if valid EIK checksum, False otherwise.
    """
    if not isinstance(eik, str):
        return False
    clean_eik = eik.strip()
    if not re.match(r"^\d{9}(\d{4})?$", clean_eik):
        return False

    digits = [int(c) for c in clean_eik]

    # 9-digit Mod 11 check
    w1_9 = [1, 2, 3, 4, 5, 6, 7, 8]
    s1 = sum(d * w for d, w in zip(digits[:8], w1_9)) % 11
    if s1 == 10:
        w2_9 = [3, 4, 5, 6, 7, 8, 9, 10]
        s1 = sum(d * w for d, w in zip(digits[:8], w2_9)) % 11
        if s1 == 10:
            s1 = 0

    if digits[8] != s1:
        return False

    # 13-digit check if present
    if len(digits) == 13:
        w1_13 = [2, 7, 3, 5]
        s2 = sum(d * w for d, w in zip(digits[8:12], w1_13)) % 11
        if s2 == 10:
            w2_13 = [4, 9, 5, 7]
            s2 = sum(d * w for d, w in zip(digits[8:12], w2_13)) % 11
            if s2 == 10:
                s2 = 0
        if digits[12] != s2:
            return False

    return True


def validate_iban(iban: str) -> bool:
    """Validates Bulgarian IBAN format and Mod-97 checksum (ISO 7064).

    Args:
        iban: IBAN string to validate.

    Returns:
        True if valid Bulgarian IBAN, False otherwise.
    """
    if not isinstance(iban, str):
        return False
    clean_iban = iban.strip().replace(" ", "").upper()
    if not re.match(r"^BG\d{2}[A-Z]{4}\d{6}[0-9A-Z]{8}$", clean_iban):
        return False

    rearranged = clean_iban[4:] + clean_iban[:4]
    numeric_str = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    try:
        return int(numeric_str) % 97 == 1
    except ValueError:
        return False


def generate_dedup_hash(
    statement_eik: str,
    doc_num: str,
    amount: float,
    posting_date: str = "",
    counterparty_iban: str = "",
    narrative: str = "",
    item_id: Any = "",
) -> str:
    """Generates SHA-256 deduplication hash for a transaction line item.

    Args:
        statement_eik: Account holder EIK/BULSTAT.
        doc_num: Document number or transaction reference.
        amount: Transaction monetary amount.
        posting_date: Transaction posting date.
        counterparty_iban: Counterparty IBAN.
        narrative: Transaction narrative description.
        item_id: Sequence index / item ID of transaction.

    Returns:
        Hexadecimal SHA-256 string.
    """
    sanitized_narrative = (narrative or "").strip().replace("\n", " ").replace("\r", " ")
    ref_doc = str(doc_num or item_id or "").strip()
    raw = (
        f"{str(statement_eik or '').strip()}|"
        f"{str(posting_date or '').strip()}|"
        f"{str(counterparty_iban or '').strip()}|"
        f"{ref_doc}|"
        f"{str(item_id or '').strip()}|"
        f"{float(amount or 0.0):.2f}|"
        f"{sanitized_narrative}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def determine_accounts(
    counterparty_name: str,
    narrative: str,
    debit_amount: float,
    credit_amount: float,
) -> Tuple[str, str]:
    """Determines debit and credit account codes according to Bulgarian Chart of Accounts.

    Account Rules:
    - Primary Bank Account: 503 (Разплащателна сметка в EUR/BGN)
    - Suppliers/Vendors: 401 (Доставчици)
    - Customers/Clients: 411 (Клиенти)
    - Tax (НАП): 454 (ДДФЛ), 455 (ДОО / ДЗПО / ЗОВ / Health), 4531/4532 (ДДС)
    - Bank Fees: 621 (Разходи за банкови такси)
    - Rent: 602 (Разходи за външни услуги - наем)

    Args:
        counterparty_name: Name of counterparty.
        narrative: Transaction description narrative.
        debit_amount: Outgoing debit amount.
        credit_amount: Incoming credit amount.

    Returns:
        Tuple of (debit_account, credit_account).
    """
    cp_upper = (counterparty_name or "").upper().strip()
    narr_upper = (narrative or "").upper().strip()

    if debit_amount > 0:
        # Outgoing payment -> Bank account 503 is credited
        credit_acc = "503"

        # Check Bank Fees / Commissions (621)
        if "БАНКА ДСК" in cp_upper or "ТАКСА" in narr_upper or "КОМИСИОНА" in narr_upper or "ПЛАН ДСК" in narr_upper:
            debit_acc = "621"
        # Check Rent Expenses (602)
        elif "HAN KRUM" in cp_upper or "НАЕМ" in narr_upper:
            debit_acc = "602"
        # Check Tax & Social Security Payments (НАП)
        elif "НАП" in cp_upper or "ДДФЛ" in narr_upper or "ДЗПО" in narr_upper or "ДОО" in narr_upper or "NCC" in narr_upper or "ДДС" in narr_upper:
            if "ДДФЛ" in narr_upper:
                debit_acc = "454"
            elif "ДЗПО" in narr_upper or "ДОО" in narr_upper or "ЗОВ" in narr_upper or "NCC" in narr_upper:
                debit_acc = "455"
            elif "ДДС" in narr_upper:
                debit_acc = "4531"
            else:
                debit_acc = "455"
        # Commercial Suppliers / Vendors (401)
        else:
            debit_acc = "401"

    elif credit_amount > 0:
        # Incoming payment -> Bank account 503 is debited
        debit_acc = "503"
        # Customers / Clients (411)
        credit_acc = "411"
    else:
        debit_acc = "503"
        credit_acc = "503"

    return debit_acc, credit_acc


def translate_transactions(input_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Translates canonical transaction JSON structure into double-entry journal entries.

    Args:
        input_data: Parsed extracted_transactions.json payload.

    Returns:
        Tuple of (metadata_dict, journal_entries_list).
    """
    metadata = input_data.get("statement_metadata", {})
    transactions = input_data.get("transactions", [])
    statement_eik = metadata.get("eik", "114077876")

    journal_entries: List[Dict[str, Any]] = []

    for tx in transactions:
        item_id = tx.get("item_id", 0)
        posting_date = tx.get("posting_date") or ""
        value_date = tx.get("value_date") or posting_date
        cp_name = tx.get("counterparty_name") or ""
        cp_iban = tx.get("counterparty_iban") or ""
        doc_no = tx.get("document_number") or ""
        debit_amt = float(tx.get("debit_amount") or 0.0)
        credit_amt = float(tx.get("credit_amount") or 0.0)
        narrative = tx.get("narrative_description") or ""
        currency = tx.get("currency") or "EUR"

        amount = debit_amt if debit_amt > 0 else credit_amt
        debit_acc, credit_acc = determine_accounts(cp_name, narrative, debit_amt, credit_amt)
        dedup_hash = generate_dedup_hash(
            statement_eik=statement_eik,
            doc_num=doc_no,
            amount=amount,
            posting_date=posting_date,
            counterparty_iban=cp_iban,
            narrative=narrative,
            item_id=item_id,
        )

        entry = {
            "item_id": item_id,
            "posting_date": posting_date,
            "value_date": value_date,
            "doc_no": doc_no,
            "counterparty_name": cp_name,
            "counterparty_iban": cp_iban,
            "counterparty_eik": "",
            "debit_account": debit_acc,
            "credit_account": credit_acc,
            "amount": amount,
            "currency": currency,
            "narrative": narrative,
            "dedup_hash": dedup_hash,
        }
        journal_entries.append(entry)

    return metadata, journal_entries


def generate_xml(metadata: Dict[str, Any], journal_entries: List[Dict[str, Any]]) -> str:
    """Generates Microinvest TransferData XML (`urn:Transfer`) double-entry export.

    Args:
        metadata: Statement metadata dictionary.
        journal_entries: List of journal entry dictionaries.

    Returns:
        XML string formatted according to Microinvest TransferData specification.
    """
    root = ET.Element("TransferData", xmlns="urn:Transfer")

    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "CompanyEIK").text = str((metadata or {}).get("eik") or "114077876")
    ET.SubElement(header, "CompanyIBAN").text = str((metadata or {}).get("iban") or "BG71STSA93000028013479")
    ET.SubElement(header, "PeriodStart").text = str((metadata or {}).get("period_start") or "01.01.2026")
    ET.SubElement(header, "PeriodEnd").text = str((metadata or {}).get("period_end") or "31.01.2026")
    ET.SubElement(header, "CreatedDate").text = "2026-01-31"

    operations = ET.SubElement(root, "Operations")
    accountings = ET.SubElement(root, "Accountings")

    for entry in journal_entries:
        item_id = str(entry.get("item_id", ""))
        posting_date = str(entry.get("posting_date") or "")
        doc_no = str(entry.get("doc_no") or "")
        cp_name = str(entry.get("counterparty_name") or "")
        cp_iban = str(entry.get("counterparty_iban") or "")
        debit_acc = str(entry.get("debit_account") or "")
        credit_acc = str(entry.get("credit_account") or "")
        amount = float(entry.get("amount") or 0.0)
        currency = str(entry.get("currency") or "EUR")
        narrative = str(entry.get("narrative") or "")
        dedup_hash = str(entry.get("dedup_hash") or "")

        op = ET.SubElement(operations, "Operation")
        ET.SubElement(op, "ItemNo").text = item_id
        ET.SubElement(op, "Date").text = posting_date
        ET.SubElement(op, "DocNum").text = doc_no
        ET.SubElement(op, "Counterparty").text = cp_name
        ET.SubElement(op, "CounterpartyIBAN").text = cp_iban
        ET.SubElement(op, "DebitAcc").text = debit_acc
        ET.SubElement(op, "CreditAcc").text = credit_acc
        ET.SubElement(op, "Amount").text = f"{amount:.2f}"
        ET.SubElement(op, "Currency").text = currency
        ET.SubElement(op, "Description").text = narrative
        ET.SubElement(op, "DedupHash").text = dedup_hash

        acc = ET.SubElement(accountings, "Accounting")
        ET.SubElement(acc, "ItemNo").text = item_id
        ET.SubElement(acc, "PostingDate").text = posting_date
        ET.SubElement(acc, "DocNum").text = doc_no
        ET.SubElement(acc, "DebitAcc").text = debit_acc
        ET.SubElement(acc, "CreditAcc").text = credit_acc
        ET.SubElement(acc, "Amount").text = f"{amount:.2f}"
        ET.SubElement(acc, "Currency").text = currency
        ET.SubElement(acc, "Narrative").text = narrative
        ET.SubElement(acc, "DedupHash").text = dedup_hash

    ET.indent(root, space="  ")
    xml_declaration = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
    return xml_declaration + ET.tostring(root, encoding="utf-8").decode("utf-8")


def generate_json(metadata: Dict[str, Any], journal_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates structured JSON ledger representation.

    Args:
        metadata: Statement metadata dictionary.
        journal_entries: List of journal entry dictionaries.

    Returns:
        Structured dictionary payload suitable for JSON serialization.
    """
    safe_entries = []
    for entry in journal_entries:
        safe_entry = {
            "item_id": entry.get("item_id", 0),
            "posting_date": entry.get("posting_date") or "",
            "value_date": entry.get("value_date") or "",
            "doc_no": entry.get("doc_no") or "",
            "counterparty_name": entry.get("counterparty_name") or "",
            "counterparty_iban": entry.get("counterparty_iban") or "",
            "counterparty_eik": entry.get("counterparty_eik") or "",
            "debit_account": entry.get("debit_account") or "",
            "credit_account": entry.get("credit_account") or "",
            "amount": float(entry.get("amount") or 0.0),
            "currency": entry.get("currency") or "EUR",
            "narrative": entry.get("narrative") or "",
            "dedup_hash": entry.get("dedup_hash") or "",
        }
        safe_entries.append(safe_entry)

    total_debit = sum(e["amount"] for e in safe_entries if e["credit_account"] == "503")
    total_credit = sum(e["amount"] for e in safe_entries if e["debit_account"] == "503")
    opening_val = (metadata or {}).get("opening_balance", 5883.29)
    opening = float(opening_val) if opening_val is not None else 5883.29
    closing = round(opening + total_credit - total_debit, 2)

    metadata_copy = dict(metadata or {})
    metadata_copy["closing_balance"] = closing

    payload = {
        "statement_metadata": metadata_copy,
        "journal_entries": safe_entries,
        "summary": {
            "total_entries": len(safe_entries),
            "total_debit_turnover": round(total_debit, 2),
            "total_credit_turnover": round(total_credit, 2),
            "net_turnover": round(total_credit - total_debit, 2),
            "opening_balance": round(opening, 2),
            "closing_balance": round(closing, 2),
        },
    }
    return payload


def sanitize_csv_field(val: Any) -> str:
    """Sanitizes a CSV field value by converting nulls to empty string,
    replacing line breaks with spaces, and replacing semicolons with spaces.
    """
    if val is None:
        return ""
    s = str(val)
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    s = s.replace(";", " ")
    return s


def generate_csv(journal_entries: List[Dict[str, Any]]) -> str:
    """Generates Bulgarian Delta CSV export.

    Args:
        journal_entries: List of journal entry dictionaries.

    Returns:
        Semicolon-separated CSV text.
    """
    headers = [
        "ItemNo",
        "PostingDate",
        "ValueDate",
        "DocumentNumber",
        "CounterpartyName",
        "CounterpartyIBAN",
        "DebitAccount",
        "CreditAccount",
        "Amount",
        "Currency",
        "Narrative",
        "DedupHash",
    ]
    lines = [";".join(headers)]

    for entry in journal_entries:
        amount_val = float(entry.get("amount") or 0.0)
        row = [
            sanitize_csv_field(entry.get("item_id", "")),
            sanitize_csv_field(entry.get("posting_date", "")),
            sanitize_csv_field(entry.get("value_date", "")),
            sanitize_csv_field(entry.get("doc_no", "")),
            sanitize_csv_field(entry.get("counterparty_name", "")),
            sanitize_csv_field(entry.get("counterparty_iban", "")),
            sanitize_csv_field(entry.get("debit_account", "")),
            sanitize_csv_field(entry.get("credit_account", "")),
            f"{amount_val:.2f}",
            sanitize_csv_field(entry.get("currency", "EUR")),
            sanitize_csv_field(entry.get("narrative", "")),
            sanitize_csv_field(entry.get("dedup_hash", "")),
        ]
        lines.append(";".join(row))

    return "\n".join(lines) + "\n"


def process_translation(input_path: str, output_dir: str) -> Dict[str, str]:
    """Processes extracted transactions JSON file and writes output artifacts.

    Args:
        input_path: Path to extracted_transactions.json.
        output_dir: Directory where xml, json, csv artifacts will be saved.

    Returns:
        Dictionary mapping artifact name to its absolute file path.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input JSON file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    metadata, journal_entries = translate_transactions(input_data)

    xml_content = generate_xml(metadata, journal_entries)
    json_payload = generate_json(metadata, journal_entries)
    csv_content = generate_csv(journal_entries)

    os.makedirs(output_dir, exist_ok=True)

    xml_path = os.path.join(output_dir, "microinvest_transferdata.xml")
    json_path = os.path.join(output_dir, "journal_entries.json")
    csv_path = os.path.join(output_dir, "delta_bg_export.csv")

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False, indent=2)

    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_content)

    return {
        "xml": os.path.abspath(xml_path),
        "json": os.path.abspath(json_path),
        "csv": os.path.abspath(csv_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate Bulgarian bank transactions into double-entry accounting files."
    )
    parser.add_argument(
        "--input",
        "-i",
        default="data/extracted_transactions.json",
        help="Path to input extracted transactions JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="data",
        help="Output directory for generated XML, JSON, and CSV files.",
    )

    args = parser.parse_args()

    try:
        written_files = process_translation(args.input, args.output_dir)
        print(f"Successfully processed {args.input}")
        for key, path in written_files.items():
            print(f"  {key.upper()}: {path}")
    except Exception as exc:
        print(f"Error processing translation: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
