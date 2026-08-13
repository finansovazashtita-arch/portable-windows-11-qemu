"""
Audit & Compliance Package.
"""

from src.audit.corporate_tax_return import (
    AnnualTaxableAdjustment,
    CorporateTaxReturn,
    CorporateTaxReturnGenerator,
    TaxableAdjustmentType,
)
from src.audit.dividend_tax_manager import DividendBeneficiaryType, DividendPayout, DividendTaxManager
from src.audit.generate_transfer_log import generate_transfer_log, reconcile_3way
from src.audit.global_tax_engine import (
    FilingFrequency,
    GlobalMultiEntityTaxEngine,
    MultiEntityTaxSummary,
    TaxableTransaction,
    TaxFilingPackage,
    TaxFilingStatus,
    TaxJurisdiction,
    TaxRate,
    TaxRegistration,
    TaxType,
)
from src.audit.nra_vat_reporter import NRAVATDeclaration, NRAVATReporter, VATPeriod
from src.audit.saft_exporter import SAFTExporter
from src.audit.swiss_estv_tax_engine import (
    SwissESTVDeclaration,
    SwissESTVTaxEngine,
    SwissFilingPeriod,
    SwissTaxMethod,
    SwissUID,
    SwissVATRate,
    SwissVATTransaction,
)
from src.audit.tax_audit_defense import AuditDefenseEvaluation, AuditRiskLevel, TaxAuditDefenseEngine
from src.audit.tax_policy_ingestor import AutonomousTaxPolicyIngestor, RegulationChangeType, TaxRegulationUpdate
from src.audit.us_sales_tax_engine import (
    TaxExemptionType,
    USNexusType,
    USSalesTaxEngine,
    USSalesTaxReturn,
    USSalesTaxTransaction,
    USStateNexus,
)

# Backward compatibility aliases
AuditReconciler3Way = reconcile_3way
TransferLogExporter = generate_transfer_log
NRAVATReport = NRAVATDeclaration

__all__ = [
    "SAFTExporter",
    "reconcile_3way",
    "generate_transfer_log",
    "AuditReconciler3Way",
    "TransferLogExporter",
    "NRAVATReporter",
    "NRAVATDeclaration",
    "NRAVATReport",
    "VATPeriod",
    "TaxAuditDefenseEngine",
    "AuditDefenseEvaluation",
    "AuditRiskLevel",
    "AutonomousTaxPolicyIngestor",
    "TaxRegulationUpdate",
    "RegulationChangeType",
    "CorporateTaxReturnGenerator",
    "CorporateTaxReturn",
    "AnnualTaxableAdjustment",
    "TaxableAdjustmentType",
    "DividendTaxManager",
    "DividendPayout",
    "DividendBeneficiaryType",
    "GlobalMultiEntityTaxEngine",
    "TaxJurisdiction",
    "TaxType",
    "FilingFrequency",
    "TaxFilingStatus",
    "TaxRate",
    "TaxRegistration",
    "TaxableTransaction",
    "TaxFilingPackage",
    "MultiEntityTaxSummary",
    "SwissESTVTaxEngine",
    "SwissVATRate",
    "SwissTaxMethod",
    "SwissFilingPeriod",
    "SwissVATTransaction",
    "SwissESTVDeclaration",
    "SwissUID",
    "USSalesTaxEngine",
    "USNexusType",
    "TaxExemptionType",
    "USStateNexus",
    "USSalesTaxTransaction",
    "USSalesTaxReturn",
]

