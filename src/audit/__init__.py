"""
Audit & Compliance Package.
"""

from src.audit.corporate_tax_return import (
    AnnualTaxableAdjustment,
    CorporateTaxReturn,
    CorporateTaxReturnGenerator,
    TaxableAdjustmentType,
)
from src.audit.generate_transfer_log import generate_transfer_log, reconcile_3way
from src.audit.nra_vat_reporter import NRAVATDeclaration, NRAVATReporter, VATPeriod
from src.audit.saft_exporter import SAFTExporter
from src.audit.tax_audit_defense import AuditDefenseEvaluation, AuditRiskLevel, TaxAuditDefenseEngine
from src.audit.tax_policy_ingestor import AutonomousTaxPolicyIngestor, RegulationChangeType, TaxRegulationUpdate

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
]
