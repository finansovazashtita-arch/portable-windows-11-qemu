"""
Accounting Package.
"""

from src.accounting.cash_desk_manager import CashDeskManager, CashDeskSummary, CashOrder, CashOrderType
from src.accounting.corporate_consolidation import (
    ConsolidatedFinancialStatement,
    CorporateConsolidationEngine,
    EntityFinancialTrialBalance,
)
from src.accounting.customs_excise_accounting import CustomsDeclaration, CustomsExciseProcessor
from src.accounting.eu_oss_accounting import EUOSSAccountingAdapter, OSSDeclarationQuarter, OSSSaleTransaction
from src.accounting.fixed_assets_depreciation import CITATaxCategory, FixedAsset, FixedAssetsDepreciationEngine
from src.accounting.fx_revaluation import FXRateProvider, FXRevaluationCalculator, FXRevaluationResult
from src.accounting.inventory_valuation import InventoryItemBatch, InventoryValuationEngine, ValuationMethod
from src.accounting.payroll_accounting import PayrollProcessor, PayrollSummary
from src.accounting.translate_to_delta import (
    generate_csv,
    generate_json,
    generate_xml,
    process_translation,
    translate_transactions,
    validate_eik,
    validate_iban,
)
from src.accounting.travel_expense_manager import (
    BusinessTravelOrder,
    BusinessTravelReport,
    TravelExpenseManager,
    TravelType,
)

# Backward-compatibility aliases
FXRevaluationEngine = FXRevaluationCalculator
PayrollAccountingEngine = PayrollProcessor
CustomsExciseAccountingEngine = CustomsExciseProcessor
generate_microinvest_xml = generate_xml
generate_delta_bg_csv = generate_csv

__all__ = [
    "validate_eik",
    "validate_iban",
    "translate_transactions",
    "generate_xml",
    "generate_csv",
    "generate_json",
    "process_translation",
    "generate_microinvest_xml",
    "generate_delta_bg_csv",
    "FXRateProvider",
    "FXRevaluationCalculator",
    "FXRevaluationEngine",
    "FXRevaluationResult",
    "PayrollProcessor",
    "PayrollAccountingEngine",
    "PayrollSummary",
    "CustomsExciseProcessor",
    "CustomsExciseAccountingEngine",
    "CustomsDeclaration",
    "EUOSSAccountingAdapter",
    "OSSSaleTransaction",
    "OSSDeclarationQuarter",
    "InventoryValuationEngine",
    "InventoryItemBatch",
    "ValuationMethod",
    "FixedAssetsDepreciationEngine",
    "FixedAsset",
    "CITATaxCategory",
    "CorporateConsolidationEngine",
    "EntityFinancialTrialBalance",
    "ConsolidatedFinancialStatement",
    "CashDeskManager",
    "CashOrder",
    "CashOrderType",
    "CashDeskSummary",
    "TravelExpenseManager",
    "BusinessTravelOrder",
    "BusinessTravelReport",
    "TravelType",
]
