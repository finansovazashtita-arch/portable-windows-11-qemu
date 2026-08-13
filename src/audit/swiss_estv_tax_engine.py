"""
Swiss Federal Tax Administration (ESTV/FTA) VAT engine module. 🇨🇭

Handles Swiss MWST (Mehrwertsteuer / TVA / IVA) VAT computation, filing,
and journal entry generation under the Swiss Federal Act on Value Added Tax (MWSTG).
"""

import enum
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger("swiss_estv_tax_engine")

class SwissVATRate(str, enum.Enum):
    STANDARD = "STANDARD"
    REDUCED = "REDUCED"
    ACCOMMODATION = "ACCOMMODATION"
    EXEMPT = "EXEMPT"
    ZERO_RATED = "ZERO_RATED"

class SwissTaxMethod(str, enum.Enum):
    EFFECTIVE_METHOD = "EFFECTIVE_METHOD"
    NET_TAX_RATE_METHOD = "NET_TAX_RATE_METHOD"
    FLAT_RATE_METHOD = "FLAT_RATE_METHOD"

class SwissFilingPeriod(str, enum.Enum):
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"

SWISS_VAT_RATES = {
    'standard': 8.1,
    'reduced': 2.6,
    'accommodation': 3.8
}

SWISS_CORPORATE_TAX_RATE = 8.5
SWISS_WITHHOLDING_TAX_RATE = 35.0

@dataclass
class SwissVATTransaction:
    transaction_id: str
    entity_id: str
    vat_rate_type: SwissVATRate
    net_amount_chf: float
    vat_rate_percent: float
    vat_amount_chf: float
    gross_amount_chf: float
    transaction_date: Optional[str] = None
    description: str = ""
    is_import: bool = False
    is_export: bool = False

@dataclass
class SwissESTVDeclaration:
    entity_id: str
    uid_number: str
    period_start: str
    period_end: str
    filing_period: SwissFilingPeriod
    cipher_200_total_revenue: float
    cipher_220_deductions: float
    cipher_221_non_taxable_services: float
    cipher_225_exempt_activities: float
    cipher_230_subsidies: float
    cipher_235_miscellaneous: float
    cipher_289_total_taxable_turnover: float
    cipher_302_standard_rate_base: float
    cipher_312_standard_rate_tax: float
    cipher_342_reduced_rate_base: float
    cipher_352_reduced_rate_tax: float
    cipher_382_accommodation_rate_base: float
    cipher_392_accommodation_rate_tax: float
    cipher_399_total_tax_due: float
    cipher_400_input_tax: float
    cipher_405_corrections: float
    cipher_410_total_input_tax: float
    cipher_500_net_tax_payable: float

@dataclass
class SwissUID:
    uid_prefix: str
    uid_number: int
    uid_suffix: str = "MWST"
    
    @property
    def formatted(self) -> str:
        num_str = f"{self.uid_number:09d}"
        return f"{self.uid_prefix}-{num_str[:3]}.{num_str[3:6]}.{num_str[6:]} {self.uid_suffix}"

class SwissESTVTaxEngine:
    @classmethod
    def validate_uid(cls, uid_string: str) -> bool:
        """
        Validates Swiss UID format: CHE-NNN.NNN.NNN [MWST|TVA|IVA]
        Includes a basic modulo 11 check digit validation.
        """
        pattern = r'^CHE-(\d{3})\.(\d{3})\.(\d{3})\s*(MWST|TVA|IVA)?$'
        match = re.match(pattern, uid_string)
        if not match:
            return False
        
        # Extract digits
        digits = match.group(1) + match.group(2) + match.group(3)
        if len(digits) != 9:
            return False
            
        # Modulo 11 check for UID (simplified)
        weights = [5, 4, 3, 2, 7, 6, 5, 4]
        checksum = 0
        for i in range(8):
            checksum += int(digits[i]) * weights[i]
            
        remainder = checksum % 11
        check_digit = 11 - remainder
        if check_digit == 11:
            check_digit = 0
        elif check_digit == 10:
            return False # Invalid check digit
            
        return check_digit == int(digits[8])

    @classmethod
    def calculate_vat(
        cls, 
        transaction_id: str, 
        entity_id: str, 
        net_amount_chf: float, 
        rate_type: SwissVATRate = SwissVATRate.STANDARD, 
        is_import: bool = False, 
        is_export: bool = False, 
        transaction_date: Optional[str] = None
    ) -> SwissVATTransaction:
        """
        Calculates Swiss VAT for a transaction based on the rate type, import/export status.
        """
        vat_rate_percent = 0.0
        
        if is_export or rate_type == SwissVATRate.ZERO_RATED:
            vat_rate_percent = 0.0
        elif rate_type == SwissVATRate.EXEMPT:
            vat_rate_percent = 0.0
        elif rate_type == SwissVATRate.STANDARD:
            vat_rate_percent = SWISS_VAT_RATES['standard']
        elif rate_type == SwissVATRate.REDUCED:
            vat_rate_percent = SWISS_VAT_RATES['reduced']
        elif rate_type == SwissVATRate.ACCOMMODATION:
            vat_rate_percent = SWISS_VAT_RATES['accommodation']
            
        vat_amount_chf = round(net_amount_chf * (vat_rate_percent / 100.0), 2)
        gross_amount_chf = round(net_amount_chf + vat_amount_chf, 2)
        
        return SwissVATTransaction(
            transaction_id=transaction_id,
            entity_id=entity_id,
            vat_rate_type=rate_type,
            net_amount_chf=net_amount_chf,
            vat_rate_percent=vat_rate_percent,
            vat_amount_chf=vat_amount_chf,
            gross_amount_chf=gross_amount_chf,
            transaction_date=transaction_date,
            is_import=is_import,
            is_export=is_export
        )

    @classmethod
    def generate_estv_declaration(
        cls, 
        entity_id: str, 
        uid_number: str, 
        period_start: str, 
        period_end: str, 
        transactions: List[SwissVATTransaction], 
        filing_period: SwissFilingPeriod = SwissFilingPeriod.QUARTERLY
    ) -> SwissESTVDeclaration:
        """
        Generates ESTV declaration summarizing transactions into cipher codes.
        """
        dec = SwissESTVDeclaration(
            entity_id=entity_id, uid_number=uid_number, 
            period_start=period_start, period_end=period_end, filing_period=filing_period,
            cipher_200_total_revenue=0.0, cipher_220_deductions=0.0, cipher_221_non_taxable_services=0.0,
            cipher_225_exempt_activities=0.0, cipher_230_subsidies=0.0, cipher_235_miscellaneous=0.0,
            cipher_289_total_taxable_turnover=0.0, cipher_302_standard_rate_base=0.0, cipher_312_standard_rate_tax=0.0,
            cipher_342_reduced_rate_base=0.0, cipher_352_reduced_rate_tax=0.0, cipher_382_accommodation_rate_base=0.0,
            cipher_392_accommodation_rate_tax=0.0, cipher_399_total_tax_due=0.0, cipher_400_input_tax=0.0,
            cipher_405_corrections=0.0, cipher_410_total_input_tax=0.0, cipher_500_net_tax_payable=0.0
        )
        
        for t in transactions:
            if not t.is_import:
                dec.cipher_200_total_revenue += t.gross_amount_chf
                
                if t.is_export:
                    dec.cipher_220_deductions += t.net_amount_chf
                elif t.vat_rate_type == SwissVATRate.EXEMPT:
                    dec.cipher_225_exempt_activities += t.net_amount_chf
                else:
                    dec.cipher_289_total_taxable_turnover += t.net_amount_chf
                    
                    if t.vat_rate_type == SwissVATRate.STANDARD:
                        dec.cipher_302_standard_rate_base += t.net_amount_chf
                        dec.cipher_312_standard_rate_tax += t.vat_amount_chf
                    elif t.vat_rate_type == SwissVATRate.REDUCED:
                        dec.cipher_342_reduced_rate_base += t.net_amount_chf
                        dec.cipher_352_reduced_rate_tax += t.vat_amount_chf
                    elif t.vat_rate_type == SwissVATRate.ACCOMMODATION:
                        dec.cipher_382_accommodation_rate_base += t.net_amount_chf
                        dec.cipher_392_accommodation_rate_tax += t.vat_amount_chf
            else:
                # Input tax
                dec.cipher_400_input_tax += t.vat_amount_chf
                
        dec.cipher_399_total_tax_due = round(
            dec.cipher_312_standard_rate_tax + 
            dec.cipher_352_reduced_rate_tax + 
            dec.cipher_392_accommodation_rate_tax, 2
        )
        
        dec.cipher_410_total_input_tax = round(dec.cipher_400_input_tax + dec.cipher_405_corrections, 2)
        dec.cipher_500_net_tax_payable = round(dec.cipher_399_total_tax_due - dec.cipher_410_total_input_tax, 2)
        
        return dec

    @classmethod
    def generate_swiss_vat_journal_entries(cls, transactions: List[SwissVATTransaction]) -> List[Dict[str, Any]]:
        """
        Generates journal entries for Swiss VAT transactions.
        """
        entries = []
        for t in transactions:
            if t.vat_amount_chf == 0:
                continue
                
            if t.is_import:
                # Input VAT
                entries.append({
                    "date": t.transaction_date,
                    "document_number": t.transaction_id,
                    "narrative": f"Swiss Input VAT on {t.transaction_id}",
                    "debit_account": "4538",
                    "debit_name": "ESTV VAT Payable",
                    "credit_account": "503",
                    "credit_name": "Trade Payables",
                    "amount": t.vat_amount_chf
                })
            else:
                # Output VAT
                entries.append({
                    "date": t.transaction_date,
                    "document_number": t.transaction_id,
                    "narrative": f"Swiss Output VAT on {t.transaction_id}",
                    "debit_account": "503",
                    "debit_name": "Trade Receivables",
                    "credit_account": "4538",
                    "credit_name": "ESTV VAT Payable",
                    "amount": t.vat_amount_chf
                })
                
        return entries

    @classmethod
    def calculate_withholding_tax(cls, gross_dividend_chf: float, beneficial_owner_country: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates Swiss Verrechnungssteuer (Withholding Tax) on dividends.
        Applies Double Taxation Agreement (DTA) rates if applicable.
        """
        dta_rates = {
            "DE": 15.0, "US": 15.0, "UK": 15.0, "FR": 15.0
        }
        
        rate = SWISS_WITHHOLDING_TAX_RATE
        if beneficial_owner_country and beneficial_owner_country in dta_rates:
            rate = dta_rates[beneficial_owner_country]
            
        withholding_amount = round(gross_dividend_chf * (rate / 100.0), 2)
        net_amount = round(gross_dividend_chf - withholding_amount, 2)
        
        return {
            "gross_amount": gross_dividend_chf,
            "withholding_rate": rate,
            "withholding_amount": withholding_amount,
            "net_amount": net_amount
        }

    @classmethod
    def generate_estv_xml_export(cls, declaration: SwissESTVDeclaration, output_path: str) -> str:
        """
        Generates ESTV-compliant XML declaration file.
        """
        root = ET.Element("ESTVDeclaration", version="1.0")
        
        entity = ET.SubElement(root, "Entity")
        ET.SubElement(entity, "UID").text = declaration.uid_number
        ET.SubElement(entity, "EntityID").text = declaration.entity_id
        
        period = ET.SubElement(root, "Period")
        ET.SubElement(period, "Start").text = declaration.period_start
        ET.SubElement(period, "End").text = declaration.period_end
        ET.SubElement(period, "Type").text = declaration.filing_period.value
        
        ciphers = ET.SubElement(root, "Ciphers")
        
        def add_cipher(parent, code, value):
            child = ET.SubElement(parent, f"Cipher_{code}")
            child.text = str(value)
            
        add_cipher(ciphers, "200", declaration.cipher_200_total_revenue)
        add_cipher(ciphers, "220", declaration.cipher_220_deductions)
        add_cipher(ciphers, "221", declaration.cipher_221_non_taxable_services)
        add_cipher(ciphers, "225", declaration.cipher_225_exempt_activities)
        add_cipher(ciphers, "230", declaration.cipher_230_subsidies)
        add_cipher(ciphers, "235", declaration.cipher_235_miscellaneous)
        add_cipher(ciphers, "289", declaration.cipher_289_total_taxable_turnover)
        add_cipher(ciphers, "302", declaration.cipher_302_standard_rate_base)
        add_cipher(ciphers, "312", declaration.cipher_312_standard_rate_tax)
        add_cipher(ciphers, "342", declaration.cipher_342_reduced_rate_base)
        add_cipher(ciphers, "352", declaration.cipher_352_reduced_rate_tax)
        add_cipher(ciphers, "382", declaration.cipher_382_accommodation_rate_base)
        add_cipher(ciphers, "392", declaration.cipher_392_accommodation_rate_tax)
        add_cipher(ciphers, "399", declaration.cipher_399_total_tax_due)
        add_cipher(ciphers, "400", declaration.cipher_400_input_tax)
        add_cipher(ciphers, "405", declaration.cipher_405_corrections)
        add_cipher(ciphers, "410", declaration.cipher_410_total_input_tax)
        add_cipher(ciphers, "500", declaration.cipher_500_net_tax_payable)
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        
        return output_path
