"""
HMRC Making Tax Digital (MTD) API adapter for VAT submissions.

This module integrates with HMRC Making Tax Digital API for:
- VAT obligations retrieval
- VAT return submission (9-box model)
- VAT liabilities and payments tracking
- Fraud prevention headers generation
"""

import enum
import logging
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("hmrc_mtd_adapter")


@dataclass
class HMRCVATObligation:
    period_key: str
    start_date: str
    end_date: str
    due_date: str
    status: str  # OPEN or FULFILLED
    received_date: Optional[str] = None


@dataclass
class HMRCVATReturn:
    period_key: str
    vat_due_sales: float                 # Box 1
    vat_due_acquisitions: float          # Box 2
    total_vat_due: float                 # Box 3
    vat_reclaimed_input: float           # Box 4
    net_vat_due: float                   # Box 5
    total_value_sales_ex_vat: float      # Box 6
    total_value_purchases_ex_vat: float  # Box 7
    total_value_goods_supplied_eu: float # Box 8
    total_acquisitions_eu: float         # Box 9
    finalised: bool


class HMRCEndpoint(str, enum.Enum):
    OBLIGATIONS = "OBLIGATIONS"
    RETURNS = "RETURNS"
    LIABILITIES = "LIABILITIES"
    PAYMENTS = "PAYMENTS"


class HMRCMTDAdapter:
    SANDBOX_BASE_URL = "https://test-api.service.hmrc.gov.uk"
    PRODUCTION_BASE_URL = "https://api.service.hmrc.gov.uk"

    @classmethod
    def generate_fraud_prevention_headers(cls, client_ip: str, vendor_software_version: str) -> Dict[str, str]:
        """
        Генерира необходимите fraud prevention хедъри (Fraud prevention headers).
        """
        logger.info(f"🇬🇧 Generating HMRC Fraud Prevention Headers for IP {client_ip}")
        return {
            "Gov-Client-Connection-Method": "DESKTOP_APP_DIRECT",
            "Gov-Client-Public-IP": client_ip,
            "Gov-Client-Public-Port": "443",
            "Gov-Client-Device-ID": "device-id-12345", 
            "Gov-Client-User-IDs": "os=mac",
            "Gov-Client-Timezone": "UTC+00:00",
            "Gov-Client-Local-IPs": "127.0.0.1",
            "Gov-Vendor-Version": vendor_software_version,
            "Gov-Vendor-License-IDs": "license-id",
            "Gov-Vendor-MAC-Addresses": "00:00:00:00:00:00"
        }

    @classmethod
    def build_vat_return_payload(cls, return_data: HMRCVATReturn) -> Dict[str, Any]:
        """
        Построява JSON payload, съответстващ на HMRC MTD VAT Returns API схема.
        """
        # Validate Box 3
        expected_box_3 = round(return_data.vat_due_sales + return_data.vat_due_acquisitions, 2)
        if round(return_data.total_vat_due, 2) != expected_box_3:
            logger.warning(f"🇬🇧 Box 3 mismatch: expected {expected_box_3}, got {return_data.total_vat_due}")

        # Validate Box 5
        expected_box_5 = round(abs(expected_box_3 - return_data.vat_reclaimed_input), 2)
        if round(return_data.net_vat_due, 2) != expected_box_5:
            logger.warning(f"🇬🇧 Box 5 mismatch: expected {expected_box_5}, got {return_data.net_vat_due}")

        return {
            "periodKey": return_data.period_key,
            "vatDueSales": round(return_data.vat_due_sales, 2),
            "vatDueAcquisitions": round(return_data.vat_due_acquisitions, 2),
            "totalVatDue": round(return_data.total_vat_due, 2),
            "vatReclaimedCurrentPeriod": round(return_data.vat_reclaimed_input, 2),
            "netVatDue": round(return_data.net_vat_due, 2),
            "totalValueSalesExVAT": int(return_data.total_value_sales_ex_vat),
            "totalValuePurchasesExVAT": int(return_data.total_value_purchases_ex_vat),
            "totalValueGoodsSuppliedExVAT": int(return_data.total_value_goods_supplied_eu),
            "totalAcquisitionsExVAT": int(return_data.total_acquisitions_eu),
            "finalised": return_data.finalised
        }

    @classmethod
    def submit_vat_return(cls, vrn: str, return_data: HMRCVATReturn, access_token: str, test_mode: bool = True) -> Dict[str, Any]:
        """
        Подава ДДС декларация към HMRC MTD API.
        """
        base_url = cls.SANDBOX_BASE_URL if test_mode else cls.PRODUCTION_BASE_URL
        url = f"{base_url}/organisations/vat/{vrn}/returns"
        
        payload = cls.build_vat_return_payload(return_data)
        data = json.dumps(payload).encode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.hmrc.1.0+json",
            "Content-Type": "application/json"
        }
        
        # Add basic fraud prevention headers
        headers.update(cls.generate_fraud_prevention_headers("127.0.0.1", "FinansProtect/2.5"))
        
        logger.info(f"🇬🇧 Submitting VAT Return for VRN {vrn} to {url}")
        
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data) if response_data else {"status": "success"}
        except urllib.error.HTTPError as e:
            logger.error(f"🇬🇧 HMRC API Error: {e.code} {e.reason}")
            try:
                error_data = e.read().decode('utf-8')
                return {"error": True, "code": e.code, "message": json.loads(error_data)}
            except Exception:
                return {"error": True, "code": e.code, "message": str(e.reason)}
        except Exception as e:
            logger.error(f"🇬🇧 Unexpected error during HMRC VAT return submission: {e}")
            return {"error": True, "message": str(e)}

    @classmethod
    def retrieve_obligations(cls, vrn: str, from_date: str, to_date: str, access_token: str, test_mode: bool = True) -> List[HMRCVATObligation]:
        """
        Извлича VAT задължения (obligations) за даден период.
        """
        base_url = cls.SANDBOX_BASE_URL if test_mode else cls.PRODUCTION_BASE_URL
        url = f"{base_url}/organisations/vat/{vrn}/obligations?from={from_date}&to={to_date}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.hmrc.1.0+json"
        }
        headers.update(cls.generate_fraud_prevention_headers("127.0.0.1", "FinansProtect/2.5"))
        
        logger.info(f"🇬🇧 Retrieving obligations for VRN {vrn} from {from_date} to {to_date}")
        
        req = urllib.request.Request(url, headers=headers, method="GET")
        obligations_list = []
        try:
            with urllib.request.urlopen(req) as response:
                response_data = response.read().decode('utf-8')
                data = json.loads(response_data)
                for obs in data.get("obligations", []):
                    obligation = HMRCVATObligation(
                        period_key=obs.get("periodKey"),
                        start_date=obs.get("start"),
                        end_date=obs.get("end"),
                        due_date=obs.get("due"),
                        status=obs.get("status"),
                        received_date=obs.get("received")
                    )
                    obligations_list.append(obligation)
        except urllib.error.HTTPError as e:
            logger.error(f"🇬🇧 HMRC API Error fetching obligations: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"🇬🇧 Unexpected error fetching obligations: {e}")
            
        return obligations_list

    @classmethod
    def calculate_vat_return_from_transactions(cls, transactions: List[Dict[str, Any]]) -> HMRCVATReturn:
        """
        Изчислява 9-те кутийки (boxes) за ДДС декларацията от сурови транзакции.
        """
        logger.info("🇬🇧 Calculating VAT Return from transactions")
        
        box1_vat_sales = 0.0
        box2_vat_acq_eu = 0.0
        box4_vat_reclaimed = 0.0
        
        box6_sales_ex = 0.0
        box7_purchases_ex = 0.0
        box8_supplies_eu = 0.0
        box9_acq_eu = 0.0
        
        for txn in transactions:
            type_code = txn.get("type")
            net_amount = txn.get("net_amount", 0.0)
            vat_amount = txn.get("vat_amount", 0.0)
            
            if type_code == "SALE":
                box1_vat_sales += vat_amount
                box6_sales_ex += net_amount
            elif type_code == "SALE_EU":
                box8_supplies_eu += net_amount
                box6_sales_ex += net_amount
            elif type_code == "PURCHASE":
                box4_vat_reclaimed += vat_amount
                box7_purchases_ex += net_amount
            elif type_code == "PURCHASE_EU":
                box2_vat_acq_eu += vat_amount
                box9_acq_eu += net_amount
                box7_purchases_ex += net_amount
                # VAT reclaimed generally includes EU acquisitions VAT if deductible
                box4_vat_reclaimed += vat_amount
                
        box3_total_vat = round(box1_vat_sales + box2_vat_acq_eu, 2)
        box5_net_vat = round(abs(box3_total_vat - box4_vat_reclaimed), 2)
        
        return HMRCVATReturn(
            period_key="CALCULATED",
            vat_due_sales=round(box1_vat_sales, 2),
            vat_due_acquisitions=round(box2_vat_acq_eu, 2),
            total_vat_due=box3_total_vat,
            vat_reclaimed_input=round(box4_vat_reclaimed, 2),
            net_vat_due=box5_net_vat,
            total_value_sales_ex_vat=round(box6_sales_ex, 2),
            total_value_purchases_ex_vat=round(box7_purchases_ex, 2),
            total_value_goods_supplied_eu=round(box8_supplies_eu, 2),
            total_acquisitions_eu=round(box9_acq_eu, 2),
            finalised=False
        )

    @classmethod
    def generate_mtd_journal_entries(cls, vat_return: HMRCVATReturn) -> List[Dict[str, Any]]:
        """
        Генерира счетоводни статии (Journal entries) за MTD ДДС декларация.
        Output VAT: Dr 503 / Cr 4536 (HMRC VAT Payable)
        Input VAT: Dr 4536 / Cr 503
        """
        logger.info("🇬🇧 Generating MTD Journal Entries for VAT settlement")
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        entries = []
        
        # Output VAT entry
        if vat_return.total_vat_due > 0:
            entries.append({
                "date": date_str,
                "document_number": f"VAT-OUT-{vat_return.period_key}",
                "narrative": "MTD Output VAT Settlement",
                "debit_account": "503",
                "debit_name": "Sales VAT",
                "credit_account": "4536",
                "credit_name": "HMRC VAT Payable",
                "amount": round(vat_return.total_vat_due, 2)
            })
            
        # Input VAT entry
        if vat_return.vat_reclaimed_input > 0:
            entries.append({
                "date": date_str,
                "document_number": f"VAT-IN-{vat_return.period_key}",
                "narrative": "MTD Input VAT Settlement",
                "debit_account": "4536",
                "debit_name": "HMRC VAT Payable",
                "credit_account": "503",
                "credit_name": "Purchases VAT",
                "amount": round(vat_return.vat_reclaimed_input, 2)
            })
            
        return entries
