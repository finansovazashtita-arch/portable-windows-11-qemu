"""
US Sales Tax Compliance Engine 🇺🇸
Provides US State Sales Tax calculation, nexus tracking, tax-exempt status detection,
and multi-state filing support for the Bulgarian accounting automation platform.
"""

import enum
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import datetime
import math

logger = logging.getLogger("audit.us_sales_tax_engine")

class USNexusType(str, enum.Enum):
    PHYSICAL_PRESENCE = "PHYSICAL_PRESENCE"
    ECONOMIC_NEXUS = "ECONOMIC_NEXUS"
    MARKETPLACE_FACILITATOR = "MARKETPLACE_FACILITATOR"
    CLICK_THROUGH_NEXUS = "CLICK_THROUGH_NEXUS"

class TaxExemptionType(str, enum.Enum):
    RESALE_CERTIFICATE = "RESALE_CERTIFICATE"
    GOVERNMENT_ENTITY = "GOVERNMENT_ENTITY"
    NONPROFIT_501C3 = "NONPROFIT_501C3"
    MANUFACTURING = "MANUFACTURING"
    AGRICULTURE = "AGRICULTURE"

@dataclass
class USStateNexus:
    state_code: str
    nexus_type: USNexusType
    established_date: str
    annual_revenue_threshold: float
    annual_transactions_threshold: int
    currently_active: bool

@dataclass
class USSalesTaxTransaction:
    transaction_id: str
    entity_id: str
    state_code: str
    gross_amount: float
    exempt_amount: float
    taxable_amount: float
    state_tax_rate: float
    combined_tax_rate: float
    tax_amount: float
    transaction_date: str
    county: Optional[str] = None
    city: Optional[str] = None

@dataclass
class USSalesTaxReturn:
    entity_id: str
    state_code: str
    period_start: str
    period_end: str
    gross_sales: float
    exempt_sales: float
    taxable_sales: float
    tax_collected: float
    tax_due: float
    penalty_amount: float
    interest_amount: float
    total_due: float

US_STATE_TAX_RATES: Dict[str, Dict[str, float]] = {
    "CA": {"state_rate": 7.25, "avg_local_rate": 1.31, "combined_rate": 8.56},
    "NY": {"state_rate": 4.0, "avg_local_rate": 4.52, "combined_rate": 8.52},
    "TX": {"state_rate": 6.25, "avg_local_rate": 1.94, "combined_rate": 8.19},
    "FL": {"state_rate": 6.0, "avg_local_rate": 1.01, "combined_rate": 7.01},
    "WA": {"state_rate": 6.5, "avg_local_rate": 2.73, "combined_rate": 9.23},
    "IL": {"state_rate": 6.25, "avg_local_rate": 2.56, "combined_rate": 8.81},
    "PA": {"state_rate": 6.0, "avg_local_rate": 0.34, "combined_rate": 6.34},
    "OH": {"state_rate": 5.75, "avg_local_rate": 1.48, "combined_rate": 7.23},
    "GA": {"state_rate": 4.0, "avg_local_rate": 3.29, "combined_rate": 7.29},
    "NC": {"state_rate": 4.75, "avg_local_rate": 2.22, "combined_rate": 6.97},
    "NJ": {"state_rate": 6.625, "avg_local_rate": 0.0, "combined_rate": 6.625},
    "VA": {"state_rate": 5.3, "avg_local_rate": 0.35, "combined_rate": 5.65},
    "MA": {"state_rate": 6.25, "avg_local_rate": 0.0, "combined_rate": 6.25},
    "AZ": {"state_rate": 5.6, "avg_local_rate": 2.77, "combined_rate": 8.37},
    "CO": {"state_rate": 2.9, "avg_local_rate": 4.82, "combined_rate": 7.72},
    "TN": {"state_rate": 7.0, "avg_local_rate": 2.55, "combined_rate": 9.55},
    "MN": {"state_rate": 6.875, "avg_local_rate": 0.58, "combined_rate": 7.455},
    "WI": {"state_rate": 5.0, "avg_local_rate": 0.44, "combined_rate": 5.44},
    "NV": {"state_rate": 6.85, "avg_local_rate": 1.38, "combined_rate": 8.23},
    "UT": {"state_rate": 6.1, "avg_local_rate": 1.09, "combined_rate": 7.19}
}

ORIGIN_BASED_STATES = {"TX", "PA", "OH", "VA", "AZ", "CA", "IL", "MO", "NM", "TN", "UT"}
NO_SALES_TAX_STATES = {"DE", "MT", "NH", "OR", "AK"}

ECONOMIC_NEXUS_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "CA": {"revenue": 500000.0, "transactions": 0},
    "NY": {"revenue": 500000.0, "transactions": 100},
    "TX": {"revenue": 500000.0, "transactions": 0},
    # Most standard states follow South Dakota v. Wayfair
    "FL": {"revenue": 100000.0, "transactions": 0},
    "default": {"revenue": 100000.0, "transactions": 200}
}

class USSalesTaxEngine:
    """
    Engine to process US Sales Tax calculations, nexus determinations,
    and returns generation.
    """

    @classmethod
    def determine_nexus(
        cls,
        entity_id: str,
        state_code: str,
        annual_revenue: float,
        annual_transactions: int,
        has_physical_presence: bool = False
    ) -> USStateNexus:
        """
        Determines nexus status based on physical presence and economic nexus thresholds.
        """
        established_date = datetime.date.today().isoformat()
        thresholds = ECONOMIC_NEXUS_THRESHOLDS.get(state_code, ECONOMIC_NEXUS_THRESHOLDS["default"])
        rev_threshold = thresholds["revenue"]
        trans_threshold = thresholds["transactions"]

        if has_physical_presence:
            nexus_type = USNexusType.PHYSICAL_PRESENCE
            currently_active = True
        else:
            has_economic = (annual_revenue >= rev_threshold) or (trans_threshold > 0 and annual_transactions >= trans_threshold)
            nexus_type = USNexusType.ECONOMIC_NEXUS
            currently_active = has_economic

        return USStateNexus(
            state_code=state_code,
            nexus_type=nexus_type,
            established_date=established_date,
            annual_revenue_threshold=rev_threshold,
            annual_transactions_threshold=trans_threshold,
            currently_active=currently_active
        )

    @classmethod
    def calculate_sales_tax(
        cls,
        transaction_id: str,
        entity_id: str,
        state_code: str,
        gross_amount: float,
        exempt_amount: float = 0.0,
        use_combined_rate: bool = True,
        transaction_date: Optional[str] = None
    ) -> USSalesTaxTransaction:
        """
        Calculates US State Sales Tax for a transaction.
        """
        if not transaction_date:
            transaction_date = datetime.date.today().isoformat()

        if state_code in NO_SALES_TAX_STATES:
            state_rate = 0.0
            combined_rate = 0.0
            tax_amount = 0.0
            taxable_amount = 0.0
            exempt_amount = gross_amount
        else:
            rates = US_STATE_TAX_RATES.get(state_code, {"state_rate": 0.0, "avg_local_rate": 0.0, "combined_rate": 0.0})
            state_rate = rates["state_rate"]
            combined_rate = rates["combined_rate"]

            rate_to_use = combined_rate if use_combined_rate else state_rate
            taxable_amount = max(0.0, gross_amount - exempt_amount)
            tax_amount = round(taxable_amount * (rate_to_use / 100.0), 2)

        return USSalesTaxTransaction(
            transaction_id=transaction_id,
            entity_id=entity_id,
            state_code=state_code,
            gross_amount=round(gross_amount, 2),
            exempt_amount=round(exempt_amount, 2),
            taxable_amount=round(taxable_amount, 2),
            state_tax_rate=state_rate,
            combined_tax_rate=combined_rate,
            tax_amount=tax_amount,
            transaction_date=transaction_date
        )

    @classmethod
    def check_tax_exemption(
        cls,
        buyer_type: str,
        state_code: str,
        exemption_certificate: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Checks if a transaction is tax exempt based on buyer type and certificate validity.
        """
        is_exempt = False
        exemption_type = None
        cert_valid = bool(exemption_certificate and len(exemption_certificate) > 5)

        buyer_map = {
            "GOVERNMENT": TaxExemptionType.GOVERNMENT_ENTITY,
            "NONPROFIT": TaxExemptionType.NONPROFIT_501C3,
            "RESELLER": TaxExemptionType.RESALE_CERTIFICATE,
            "MANUFACTURER": TaxExemptionType.MANUFACTURING,
            "FARMER": TaxExemptionType.AGRICULTURE
        }

        b_type_upper = buyer_type.upper()
        if b_type_upper in buyer_map and cert_valid:
            is_exempt = True
            exemption_type = buyer_map[b_type_upper].value

        return {
            "is_exempt": is_exempt,
            "exemption_type": exemption_type,
            "certificate_valid": cert_valid
        }

    @classmethod
    def generate_state_tax_return(
        cls,
        entity_id: str,
        state_code: str,
        period_start: str,
        period_end: str,
        transactions: List[USSalesTaxTransaction]
    ) -> USSalesTaxReturn:
        """
        Generates a state sales tax return aggregating sales data and calculating penalties if applicable.
        """
        gross_sales = 0.0
        exempt_sales = 0.0
        taxable_sales = 0.0
        tax_collected = 0.0

        for tx in transactions:
            if tx.state_code == state_code:
                gross_sales += tx.gross_amount
                exempt_sales += tx.exempt_amount
                taxable_sales += tx.taxable_amount
                tax_collected += tx.tax_amount

        # Simplified penalty logic for demonstration (assuming late filing check would happen here)
        # For this example, we assume filed on time so penalty/interest = 0
        penalty_amount = 0.0
        interest_amount = 0.0
        
        tax_due = tax_collected
        total_due = tax_due + penalty_amount + interest_amount

        return USSalesTaxReturn(
            entity_id=entity_id,
            state_code=state_code,
            period_start=period_start,
            period_end=period_end,
            gross_sales=round(gross_sales, 2),
            exempt_sales=round(exempt_sales, 2),
            taxable_sales=round(taxable_sales, 2),
            tax_collected=round(tax_collected, 2),
            tax_due=round(tax_due, 2),
            penalty_amount=round(penalty_amount, 2),
            interest_amount=round(interest_amount, 2),
            total_due=round(total_due, 2)
        )

    @classmethod
    def generate_sales_tax_journal_entries(
        cls,
        transactions: List[USSalesTaxTransaction]
    ) -> List[Dict[str, Any]]:
        """
        Generates Bulgarian accounting journal entries for US Sales Tax liabilities.
        """
        journal_entries = []
        for tx in transactions:
            if tx.tax_amount > 0:
                # Assuming amount is already converted to EUR or standard currency
                je = {
                    "date": tx.transaction_date,
                    "document_number": tx.transaction_id,
                    "narrative": f"US Sales Tax Liability - {tx.state_code}",
                    "debit_account": "503",
                    "debit_name": "Разплащателна сметка",
                    "credit_account": "4537",
                    "credit_name": "US State Sales Tax Payable",
                    "amount": tx.tax_amount
                }
                journal_entries.append(je)
        return journal_entries

    @classmethod
    def generate_multi_state_summary(
        cls,
        entity_id: str,
        transactions: List[USSalesTaxTransaction]
    ) -> Dict[str, Any]:
        """
        Generates a summary of tax liabilities across all US states.
        """
        state_totals: Dict[str, Dict[str, float]] = {}
        total_tax_liability = 0.0
        total_gross_sales = 0.0

        for tx in transactions:
            if tx.state_code not in state_totals:
                state_totals[tx.state_code] = {
                    "gross_sales": 0.0,
                    "tax_collected": 0.0
                }
            state_totals[tx.state_code]["gross_sales"] += tx.gross_amount
            state_totals[tx.state_code]["tax_collected"] += tx.tax_amount
            total_gross_sales += tx.gross_amount
            total_tax_liability += tx.tax_amount
        
        # Format the numbers
        for state in state_totals:
            state_totals[state]["gross_sales"] = round(state_totals[state]["gross_sales"], 2)
            state_totals[state]["tax_collected"] = round(state_totals[state]["tax_collected"], 2)

        return {
            "entity_id": entity_id,
            "total_gross_sales": round(total_gross_sales, 2),
            "total_tax_liability": round(total_tax_liability, 2),
            "state_breakdown": state_totals
        }
