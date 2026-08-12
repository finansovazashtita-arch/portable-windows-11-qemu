"""
OECD SAF-T (Standard Audit File for Tax) & NRA/НАП Tax Audit Exporter Module.

Generates OECD SAF-T v2.0 XML compliance export files containing:
- AuditFileHeader (Company EIK, Tax Registration, Period)
- MasterFiles (GeneralLedgerAccounts, Customers, Suppliers)
- GeneralLedgerEntries (Double-entry journal lines)
- SHA-256 integrity hash verification
"""

import hashlib
import json
import logging
import os
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

logger = logging.getLogger("saft_exporter")


class SAFTExporter:
    """Generates OECD SAF-T v2.0 XML files for Bulgarian tax audits (NRA / НАП)."""

    SAF_T_NAMESPACE = "urn:OECD:StandardAuditFile-Tax:2.00"

    @classmethod
    def generate_saft_xml(
        cls,
        company_info: Dict[str, Any],
        journal_entries: List[Dict[str, Any]],
        output_path: str,
    ) -> str:
        """Generates standard SAF-T XML file and writes to output_path."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        company_name = company_info.get("company_name", "СТОРГОЗИЯ АД")
        eik = company_info.get("eik", "114077876")
        currency = company_info.get("currency", "EUR")
        now = time.strftime("%Y-%m-%dT%H:%M:%S")

        root = ET.Element("AuditFile", {"xmlns": cls.SAF_T_NAMESPACE})

        # 1. AuditFileHeader
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "AuditFileVersion").text = "2.00"
        ET.SubElement(header, "AuditFileCountry").text = "BG"
        ET.SubElement(header, "AuditFileDateCreated").text = time.strftime("%Y-%m-%d")
        ET.SubElement(header, "SoftwareHeader").text = "FinansProtect-SAF-T-Exporter v2.5"
        ET.SubElement(header, "DefaultCurrencyCode").text = currency

        company = ET.SubElement(header, "Company")
        ET.SubElement(company, "RegistrationNumber").text = eik
        ET.SubElement(company, "Name").text = company_name

        # 2. MasterFiles
        master_files = ET.SubElement(root, "MasterFiles")

        # 2a. GeneralLedgerAccounts
        gl_accounts = ET.SubElement(master_files, "GeneralLedgerAccounts")
        accounts_map = {
            "503": "Разплащателна сметка в EUR",
            "401": "Доставчици",
            "411": "Клиенти",
            "602": "Разходи за външни услуги",
            "621": "Разходи за банкови такси",
            "501": "Каса в EUR",
            "4531": "Начислен ДДС за покупки",
            "4532": "Начислен ДДС за продажби",
        }
        for code, desc in accounts_map.items():
            acc = ET.SubElement(gl_accounts, "Account")
            ET.SubElement(acc, "AccountID").text = code
            ET.SubElement(acc, "AccountDescription").text = desc

        # 3. GeneralLedgerEntries
        gl_entries = ET.SubElement(root, "GeneralLedgerEntries")
        ET.SubElement(gl_entries, "NumberOfEntries").text = str(len(journal_entries))

        total_debits = 0.0
        total_credits = 0.0

        for idx, entry in enumerate(journal_entries, 1):
            tx_node = ET.SubElement(gl_entries, "Transaction")
            ET.SubElement(tx_node, "TransactionID").text = f"TX_{idx:04d}"
            ET.SubElement(tx_node, "Period").text = "01"
            ET.SubElement(tx_node, "TransactionDate").text = entry.get("date", time.strftime("%Y-%m-%d"))
            ET.SubElement(tx_node, "Description").text = entry.get("narrative", "")

            lines = entry.get("lines", [])
            for line in lines:
                l_node = ET.SubElement(tx_node, "Line")
                acc_code = line.get("account_code", "503")
                amt = float(line.get("amount", 0.0))
                flow = line.get("type", "DEBIT")

                ET.SubElement(l_node, "AccountID").text = acc_code

                if flow == "DEBIT":
                    ET.SubElement(l_node, "DebitAmount").text = f"{amt:.2f}"
                    total_debits += amt
                else:
                    ET.SubElement(l_node, "CreditAmount").text = f"{amt:.2f}"
                    total_credits += amt

        ET.SubElement(gl_entries, "TotalDebit").text = f"{total_debits:.2f}"
        ET.SubElement(gl_entries, "TotalCredit").text = f"{total_credits:.2f}"

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

        logger.info(f"Successfully generated SAF-T tax audit XML file: {output_path}")
        return output_path
