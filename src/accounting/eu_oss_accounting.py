"""
Autonomous Cross-Border EU Tax & OSS (One-Stop-Shop) E-Commerce Invoicing Adapter.

Handles accounting and VAT declarations for cross-border EU e-commerce B2C sales:
- Multi-country EU VAT rate calculations (DE 19%, FR 20%, IT 22%, ES 21%, RO 19%, etc.)
- Double-entry mapping: Sales revenue (702), Cash/Bank (503), EU OSS VAT Payable (4535)
- Quarterly OSS declaration summary package generation
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("eu_oss_accounting")

EU_VAT_RATES = {
    "DE": 19.0,
    "FR": 20.0,
    "IT": 22.0,
    "ES": 21.0,
    "RO": 19.0,
    "GR": 24.0,
    "AT": 20.0,
    "NL": 21.0,
    "BE": 21.0,
    "PL": 23.0,
}


class OSSDeclarationQuarter(str, enum.Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


@dataclasses.dataclass
class OSSSaleTransaction:
    """Dataclass holding cross-border EU B2C sale details."""

    transaction_id: str
    country_code: str
    net_amount_eur: float
    vat_rate_percent: float
    vat_amount_eur: float
    gross_amount_eur: float


class EUOSSAccountingAdapter:
    """Adapter for processing EU One-Stop-Shop (OSS) e-commerce sales and VAT declarations."""

    @classmethod
    def process_eu_b2c_sale(
        cls, transaction_id: str, country_code: str, net_amount_eur: float
    ) -> OSSSaleTransaction:
        """Processes cross-border EU B2C sale with member-state VAT rate."""
        cc = country_code.upper().strip()
        vat_rate = EU_VAT_RATES.get(cc, 20.0)

        vat_amount = round(net_amount_eur * (vat_rate / 100.0), 2)
        gross_amount = round(net_amount_eur + vat_amount, 2)

        tx = OSSSaleTransaction(
            transaction_id=transaction_id,
            country_code=cc,
            net_amount_eur=net_amount_eur,
            vat_rate_percent=vat_rate,
            vat_amount_eur=vat_amount,
            gross_amount_eur=gross_amount,
        )
        logger.info(f"💶 Processed EU OSS B2C Sale [{transaction_id}] to {cc}: Net={net_amount_eur} EUR, VAT ({vat_rate}%)={vat_amount} EUR")
        return tx

    @classmethod
    def generate_oss_journal_entries(cls, sales: List[OSSSaleTransaction]) -> List[Dict[str, Any]]:
        """Generates double-entry journal entries for EU OSS sales."""
        entries = []
        for tx in sales:
            entries.append(
                {
                    "doc_num": tx.transaction_id,
                    "account_dr": "503",  # Bank / Payment Gateway
                    "account_cr": "702",  # Goods Sales Revenue
                    "amount_eur": tx.net_amount_eur,
                    "narrative": f"EU OSS Sale Revenue ({tx.country_code})",
                }
            )
            entries.append(
                {
                    "doc_num": tx.transaction_id,
                    "account_dr": "503",  # Bank / Payment Gateway
                    "account_cr": "4535",  # EU OSS VAT Payable
                    "amount_eur": tx.vat_amount_eur,
                    "narrative": f"EU OSS VAT Payable {tx.vat_rate_percent}% ({tx.country_code})",
                }
            )
        return entries

    @classmethod
    def generate_quarterly_oss_report(
        cls, year: int, quarter: OSSDeclarationQuarter, sales: List[OSSSaleTransaction]
    ) -> Dict[str, Any]:
        """Generates quarterly EU OSS VAT declaration summary."""
        total_net = sum(s.net_amount_eur for s in sales)
        total_vat = sum(s.vat_amount_eur for s in sales)
        total_gross = sum(s.gross_amount_eur for s in sales)

        by_country: Dict[str, Dict[str, float]] = {}
        for s in sales:
            if s.country_code not in by_country:
                by_country[s.country_code] = {"net": 0.0, "vat": 0.0}
            by_country[s.country_code]["net"] = round(by_country[s.country_code]["net"] + s.net_amount_eur, 2)
            by_country[s.country_code]["vat"] = round(by_country[s.country_code]["vat"] + s.vat_amount_eur, 2)

        return {
            "year": year,
            "quarter": quarter.value,
            "total_sales_count": len(sales),
            "total_net_eur": round(total_net, 2),
            "total_vat_eur": round(total_vat, 2),
            "total_gross_eur": round(total_gross, 2),
            "country_breakdown": by_country,
        }
