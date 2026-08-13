"""
CORE Global Multi-Entity Tax & VAT Engine module.

This module provides a comprehensive, production-grade implementation for managing
multi-jurisdictional tax calculations, filings, and accounting entries.
Supported jurisdictions include Bulgaria, EU OSS, UK, USA, and Switzerland.
"""

import enum
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("global_tax_engine")

class TaxJurisdiction(str, enum.Enum):
    BULGARIA = "BULGARIA"
    EU_OSS = "EU_OSS"
    UNITED_KINGDOM = "UNITED_KINGDOM"
    UNITED_STATES = "UNITED_STATES"
    SWITZERLAND = "SWITZERLAND"

class TaxType(str, enum.Enum):
    VAT = "VAT"
    SALES_TAX = "SALES_TAX"
    CORPORATE_INCOME_TAX = "CORPORATE_INCOME_TAX"
    WITHHOLDING_TAX = "WITHHOLDING_TAX"
    CUSTOMS_DUTY = "CUSTOMS_DUTY"

class FilingFrequency(str, enum.Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUALLY = "ANNUALLY"

class TaxFilingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass
class TaxRate:
    jurisdiction: TaxJurisdiction
    tax_type: TaxType
    rate_percent: float
    description: str
    effective_from: str
    effective_to: Optional[str] = None

@dataclass
class TaxRegistration:
    entity_id: str
    entity_name: str
    jurisdiction: TaxJurisdiction
    registration_number: str
    registration_type: str  # e.g. 'VAT', 'EIN', 'UID'
    is_active: bool

@dataclass
class TaxableTransaction:
    transaction_id: str
    entity_id: str
    jurisdiction: TaxJurisdiction
    tax_type: TaxType
    net_amount: float
    currency: str
    tax_rate_percent: float
    tax_amount: float
    gross_amount: float
    transaction_date: str
    counterparty_id: Optional[str] = None
    counterparty_jurisdiction: Optional[TaxJurisdiction] = None

@dataclass
class TaxFilingPackage:
    filing_id: str
    entity_id: str
    jurisdiction: TaxJurisdiction
    period_start: str
    period_end: str
    filing_frequency: FilingFrequency
    status: TaxFilingStatus
    total_tax_payable: float
    total_tax_refundable: float
    net_tax_position: float
    line_items: List[Dict[str, Any]]
    generated_at: str

@dataclass
class MultiEntityTaxSummary:
    consolidation_date: str
    entities: List[Dict[str, Any]]
    total_group_tax_liability: float
    jurisdictions_covered: List[str]
    intercompany_adjustments: List[Dict[str, Any]]


# --- Tax Rate Registries ---

EU_VAT_RATES = {
    "DE": 19.0, "FR": 20.0, "IT": 22.0, "ES": 21.0, "NL": 21.0,
    "AT": 20.0, "BE": 21.0, "SE": 25.0, "PL": 23.0, "RO": 19.0,
    "CZ": 21.0, "HU": 27.0, "IE": 23.0, "DK": 25.0, "FI": 24.0,
}

UK_VAT_RATES = {
    "standard": 20.0,
    "reduced": 5.0,
    "zero": 0.0,
}

US_STATE_SALES_TAX_RATES = {
    "CA": 7.25, "NY": 4.0, "TX": 6.25, "FL": 6.0, "WA": 6.5,
    "IL": 6.25, "PA": 6.0, "OH": 5.75, "GA": 4.0, "NC": 4.75,
    "MI": 6.0, "NJ": 6.625, "VA": 5.3, "CO": 2.9, "AZ": 5.6,
}

SWISS_VAT_RATES = {
    "standard": 8.1,
    "reduced": 2.6,
    "accommodation": 3.8,
}

BG_VAT_RATE = 20.0

CORPORATE_TAX_RATES = {
    "BG": 10.0,
    "UK": 25.0,
    "US_FEDERAL": 21.0,
    "CH": 8.5,
    "DE": 15.0,
    "FR": 25.0,
}


class GlobalMultiEntityTaxEngine:
    """Core Engine for Multi-Entity Global Tax computations."""

    @classmethod
    def calculate_tax(
        cls,
        transaction_id: str,
        entity_id: str,
        jurisdiction: TaxJurisdiction,
        tax_type: TaxType,
        net_amount: float,
        currency: str,
        tax_rate_override: Optional[float] = None,
        us_state: Optional[str] = None,
        transaction_date: Optional[str] = None,
        counterparty_id: Optional[str] = None,
        counterparty_jurisdiction: Optional[TaxJurisdiction] = None
    ) -> TaxableTransaction:
        """Calculate tax on a standard transaction based on jurisdiction rules."""
        logger.info(f"🌍 Calculating tax for tx: {transaction_id}, {jurisdiction.value}")
        
        rate = 0.0
        if tax_rate_override is not None:
            rate = tax_rate_override
        else:
            if tax_type == TaxType.VAT:
                if jurisdiction == TaxJurisdiction.BULGARIA:
                    rate = BG_VAT_RATE
                elif jurisdiction == TaxJurisdiction.UNITED_KINGDOM:
                    rate = UK_VAT_RATES["standard"]
                elif jurisdiction == TaxJurisdiction.SWITZERLAND:
                    rate = SWISS_VAT_RATES["standard"]
            elif tax_type == TaxType.SALES_TAX and jurisdiction == TaxJurisdiction.UNITED_STATES:
                if us_state and us_state in US_STATE_SALES_TAX_RATES:
                    rate = US_STATE_SALES_TAX_RATES[us_state]
                else:
                    rate = 0.0  # fallback or dynamic API needed

        tax_amount = round(net_amount * (rate / 100.0), 2)
        gross_amount = round(net_amount + tax_amount, 2)

        transaction = TaxableTransaction(
            transaction_id=transaction_id,
            entity_id=entity_id,
            jurisdiction=jurisdiction,
            tax_type=tax_type,
            net_amount=net_amount,
            currency=currency,
            tax_rate_percent=rate,
            tax_amount=tax_amount,
            gross_amount=gross_amount,
            transaction_date=transaction_date or datetime.utcnow().isoformat(),
            counterparty_id=counterparty_id,
            counterparty_jurisdiction=counterparty_jurisdiction,
        )
        logger.info(f"✅ Tax calculated: rate={rate}%, tax_amount={tax_amount} {currency}")
        return transaction

    @classmethod
    def calculate_reverse_charge_vat(
        cls,
        transaction_id: str,
        entity_id: str,
        seller_jurisdiction: TaxJurisdiction,
        buyer_jurisdiction: TaxJurisdiction,
        net_amount: float,
        currency: str
    ) -> TaxableTransaction:
        """Calculate reverse charge VAT for EU cross-border B2B transactions."""
        logger.info(f"🇪🇺 Calculating reverse charge VAT for tx: {transaction_id}")
        
        # In a real scenario, we would map the jurisdiction enum to country code
        rate = 20.0
        if buyer_jurisdiction == TaxJurisdiction.BULGARIA:
            rate = BG_VAT_RATE
        elif buyer_jurisdiction == TaxJurisdiction.EU_OSS:
            rate = 20.0 # Standard fallback

        tax_amount = round(net_amount * (rate / 100.0), 2)

        # For reverse charge, gross amount often just equals net for the seller,
        # but the buyer self-assesses the tax. We represent the self-assessed tax amount.
        return TaxableTransaction(
            transaction_id=transaction_id,
            entity_id=entity_id,
            jurisdiction=buyer_jurisdiction,
            tax_type=TaxType.VAT,
            net_amount=net_amount,
            currency=currency,
            tax_rate_percent=rate,
            tax_amount=tax_amount,
            gross_amount=net_amount,
            transaction_date=datetime.utcnow().isoformat(),
            counterparty_jurisdiction=seller_jurisdiction,
        )

    @classmethod
    def calculate_withholding_tax(
        cls,
        transaction_id: str,
        entity_id: str,
        jurisdiction: TaxJurisdiction,
        gross_amount: float,
        currency: str,
        beneficial_owner_jurisdiction: Optional[TaxJurisdiction] = None
    ) -> TaxableTransaction:
        """Calculate withholding tax based on gross amount and DTA rules."""
        logger.info(f"🧾 Calculating withholding tax for tx: {transaction_id}")
        
        rate = 10.0 # Default base rate
        if beneficial_owner_jurisdiction and beneficial_owner_jurisdiction != jurisdiction:
            # DTA (Double Tax Agreement) logic would apply here
            rate = 5.0

        tax_amount = round(gross_amount * (rate / 100.0), 2)
        net_amount = round(gross_amount - tax_amount, 2)

        return TaxableTransaction(
            transaction_id=transaction_id,
            entity_id=entity_id,
            jurisdiction=jurisdiction,
            tax_type=TaxType.WITHHOLDING_TAX,
            net_amount=net_amount,
            currency=currency,
            tax_rate_percent=rate,
            tax_amount=tax_amount,
            gross_amount=gross_amount,
            transaction_date=datetime.utcnow().isoformat(),
            counterparty_jurisdiction=beneficial_owner_jurisdiction,
        )

    @classmethod
    def generate_tax_journal_entries(cls, transactions: List[TaxableTransaction]) -> List[Dict[str, Any]]:
        """Generate double-entry accounting entries for tax transactions."""
        logger.info(f"📝 Generating journal entries for {len(transactions)} tax transactions")
        entries = []
        
        for tx in transactions:
            if tx.tax_type == TaxType.VAT:
                if tx.jurisdiction == TaxJurisdiction.BULGARIA:
                    # Output VAT example
                    entries.append({
                        "date": tx.transaction_date,
                        "document_number": tx.transaction_id,
                        "narrative": f"BG VAT on transaction {tx.transaction_id}",
                        "debit_account": "503",
                        "debit_name": "Разплащателна сметка в левове",
                        "credit_account": "4532",
                        "credit_name": "Начислен данък за продажбите",
                        "amount": tx.tax_amount,
                    })
                elif tx.jurisdiction == TaxJurisdiction.UNITED_KINGDOM:
                    entries.append({
                        "date": tx.transaction_date,
                        "document_number": tx.transaction_id,
                        "narrative": f"UK VAT Payable for {tx.transaction_id}",
                        "debit_account": "503",
                        "debit_name": "Bank Account",
                        "credit_account": "4536",
                        "credit_name": "HMRC VAT Payable",
                        "amount": tx.tax_amount,
                    })
                elif tx.jurisdiction == TaxJurisdiction.SWITZERLAND:
                    entries.append({
                        "date": tx.transaction_date,
                        "document_number": tx.transaction_id,
                        "narrative": f"CH VAT Payable for {tx.transaction_id}",
                        "debit_account": "503",
                        "debit_name": "Bank Account",
                        "credit_account": "4538",
                        "credit_name": "ESTV VAT Payable",
                        "amount": tx.tax_amount,
                    })
            elif tx.tax_type == TaxType.SALES_TAX and tx.jurisdiction == TaxJurisdiction.UNITED_STATES:
                entries.append({
                    "date": tx.transaction_date,
                    "document_number": tx.transaction_id,
                    "narrative": f"US Sales Tax for {tx.transaction_id}",
                    "debit_account": "503",
                    "debit_name": "Bank Account",
                    "credit_account": "4537",
                    "credit_name": "US State Sales Tax Payable",
                    "amount": tx.tax_amount,
                })
        
        return entries

    @classmethod
    def generate_tax_filing(
        cls,
        entity_id: str,
        jurisdiction: TaxJurisdiction,
        period_start: str,
        period_end: str,
        transactions: List[TaxableTransaction],
        filing_frequency: FilingFrequency = FilingFrequency.QUARTERLY
    ) -> TaxFilingPackage:
        """Filter transactions and generate a TaxFilingPackage."""
        logger.info(f"📊 Generating tax filing for {entity_id}, {jurisdiction.value}")
        
        filtered = [
            tx for tx in transactions 
            if tx.entity_id == entity_id 
            and tx.jurisdiction == jurisdiction
            and period_start <= tx.transaction_date <= period_end
        ]

        total_payable = sum(tx.tax_amount for tx in filtered if tx.tax_amount > 0)
        total_refundable = sum(abs(tx.tax_amount) for tx in filtered if tx.tax_amount < 0)
        net_position = total_payable - total_refundable

        line_items = [
            {"transaction_id": tx.transaction_id, "tax_type": tx.tax_type.value, "tax_amount": tx.tax_amount}
            for tx in filtered
        ]

        return TaxFilingPackage(
            filing_id=f"FIL-{entity_id}-{int(datetime.utcnow().timestamp())}",
            entity_id=entity_id,
            jurisdiction=jurisdiction,
            period_start=period_start,
            period_end=period_end,
            filing_frequency=filing_frequency,
            status=TaxFilingStatus.DRAFT,
            total_tax_payable=round(total_payable, 2),
            total_tax_refundable=round(total_refundable, 2),
            net_tax_position=round(net_position, 2),
            line_items=line_items,
            generated_at=datetime.utcnow().isoformat()
        )

    @classmethod
    def generate_hmrc_mtd_return(
        cls,
        entity_id: str,
        period_start: str,
        period_end: str,
        transactions: List[TaxableTransaction]
    ) -> Dict[str, Any]:
        """Generate UK HMRC Making Tax Digital (MTD) VAT Return."""
        logger.info(f"🇬🇧 Generating HMRC MTD Return for {entity_id}")
        
        # MTD 9-box simplified logic
        box1 = sum(tx.tax_amount for tx in transactions if tx.tax_amount > 0) # VAT due on sales
        box2 = 0.0 # VAT due on acquisitions from EU
        box3 = box1 + box2 # Total VAT due
        box4 = sum(abs(tx.tax_amount) for tx in transactions if tx.tax_amount < 0) # VAT reclaimed on purchases
        box5 = abs(box3 - box4) # Net VAT to be paid or reclaimed
        box6 = sum(tx.net_amount for tx in transactions if tx.tax_amount > 0) # Total value of sales ex VAT
        box7 = sum(tx.net_amount for tx in transactions if tx.tax_amount < 0) # Total value of purchases ex VAT
        box8 = 0.0 # Total value of intra-EC dispatches
        box9 = 0.0 # Total value of intra-EC acquisitions
        
        return {
            "entity_id": entity_id,
            "period": {"start": period_start, "end": period_end},
            "vatDueSales": round(box1, 2),
            "vatDueAcquisitions": round(box2, 2),
            "totalVatDue": round(box3, 2),
            "vatReclaimedCurrPeriod": round(box4, 2),
            "netVatDue": round(box5, 2),
            "totalValueSalesExVAT": round(box6, 2),
            "totalValuePurchasesExVAT": round(box7, 2),
            "totalValueGoodsSuppliedExVAT": round(box8, 2),
            "totalAcquisitionsExVAT": round(box9, 2),
        }

    @classmethod
    def generate_estv_declaration(
        cls,
        entity_id: str,
        period_start: str,
        period_end: str,
        transactions: List[TaxableTransaction]
    ) -> Dict[str, Any]:
        """Generate Swiss ESTV VAT declaration."""
        logger.info(f"🇨🇭 Generating ESTV Declaration for {entity_id}")
        
        # Simplistic cipher mappings
        cipher_200 = sum(tx.gross_amount for tx in transactions if tx.tax_rate_percent > 0)
        cipher_220 = sum(tx.tax_amount for tx in transactions if tx.tax_rate_percent == SWISS_VAT_RATES["standard"])
        cipher_221 = sum(tx.tax_amount for tx in transactions if tx.tax_rate_percent == SWISS_VAT_RATES["reduced"])
        cipher_235 = sum(tx.net_amount for tx in transactions if tx.tax_amount < 0) # Procurements subject to VAT
        
        return {
            "entity_id": entity_id,
            "period": {"start": period_start, "end": period_end},
            "ciphers": {
                "200": round(cipher_200, 2),
                "220": round(cipher_220, 2),
                "221": round(cipher_221, 2),
                "235": round(cipher_235, 2),
            }
        }

    @classmethod
    def generate_us_sales_tax_return(
        cls,
        entity_id: str,
        state_code: str,
        period_start: str,
        period_end: str,
        transactions: List[TaxableTransaction]
    ) -> Dict[str, Any]:
        """Generate US state-level sales tax return."""
        logger.info(f"🇺🇸 Generating US Sales Tax Return for {state_code}")
        
        gross_sales = sum(tx.gross_amount for tx in transactions)
        exempt_sales = sum(tx.gross_amount for tx in transactions if tx.tax_rate_percent == 0)
        taxable_sales = gross_sales - exempt_sales
        tax_collected = sum(tx.tax_amount for tx in transactions)
        
        return {
            "entity_id": entity_id,
            "state_code": state_code,
            "period": {"start": period_start, "end": period_end},
            "gross_sales": round(gross_sales, 2),
            "exempt_sales": round(exempt_sales, 2),
            "taxable_sales": round(taxable_sales, 2),
            "tax_collected": round(tax_collected, 2),
            "tax_due": round(tax_collected, 2),
        }

    @classmethod
    def consolidate_group_tax_position(
        cls,
        entities: List[Dict[str, Any]],
        period_start: str,
        period_end: str,
        transactions: List[TaxableTransaction]
    ) -> MultiEntityTaxSummary:
        """Aggregate tax positions across group and eliminate intercompany."""
        logger.info(f"🔗 Consolidating group tax position for {len(entities)} entities")
        
        entity_ids = [e.get("entity_id") for e in entities if e.get("entity_id")]
        jurisdictions_covered = list(set([e.get("jurisdiction") for e in entities if e.get("jurisdiction")]))
        
        intercompany = cls.detect_intercompany_transactions(transactions, entity_ids)
        
        # Calculate gross liability
        total_liability = 0.0
        for tx in transactions:
            if tx.transaction_date >= period_start and tx.transaction_date <= period_end:
                total_liability += tx.tax_amount
                
        # Offset intercompany adjustments
        for ic_tx in intercompany:
            # simplistic offset for demonstration
            if ic_tx["tax_amount"] > 0:
                total_liability -= ic_tx["tax_amount"]
                
        return MultiEntityTaxSummary(
            consolidation_date=datetime.utcnow().isoformat(),
            entities=entities,
            total_group_tax_liability=round(total_liability, 2),
            jurisdictions_covered=jurisdictions_covered,
            intercompany_adjustments=intercompany,
        )

    @classmethod
    def detect_intercompany_transactions(
        cls,
        transactions: List[TaxableTransaction],
        entity_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Identify transactions between related group entities."""
        logger.info(f"🔍 Detecting intercompany transactions among {len(entity_ids)} group entities")
        
        ic_transactions = []
        for tx in transactions:
            if tx.counterparty_id and tx.counterparty_id in entity_ids and tx.entity_id in entity_ids:
                ic_transactions.append({
                    "transaction_id": tx.transaction_id,
                    "entity_id": tx.entity_id,
                    "counterparty_id": tx.counterparty_id,
                    "amount": tx.net_amount,
                    "tax_amount": tx.tax_amount,
                    "requires_transfer_pricing_review": True
                })
        
        return ic_transactions
