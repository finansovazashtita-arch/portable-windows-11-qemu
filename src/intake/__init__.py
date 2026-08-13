"""
Intake Package.
"""

from src.intake.bank_feed_guard import BankFeedGuard, BankFeedItem, BankFeedStatus, ReconciliationSummary
from src.intake.email_parser import EmailIntakeResult, EmailStatementParser
from src.intake.open_banking_pisp import OpenBankingPISPAggregator, PaymentInitiationRequest, PaymentInitiationResult
from src.intake.psd2_openbanking import PSD2BankProvider, PSD2OpenBankingClient
from src.intake.sepa_bisera_instant import InstantPaymentTransaction, PaymentSystem, SEPABiseraInstantAdapter

# M83 CEE Open Banking PISP/AISP Expansion
from src.intake.cee_open_banking_aggregator import (
    CEEOpenBankingAggregator,
    CEEBankCode,
    CEEBankProfile,
    CEECountry,
    CEECurrency,
    CEEApiEnvironment,
    CEEConsentToken,
    CEEAccountBalance,
    CEETransaction,
    CEEPaymentResult,
    CEEAggregatedBalance,
    CEEPaymentBatchResult,
    PIISPStatus,
    CEE_BANK_REGISTRY,
    # Validator helpers
    validate_iban_cee,
    validate_polish_nip,
    validate_romanian_cif,
    validate_greek_afm,
)

# Backward compatibility aliases
ExtractedEmailPayload = EmailIntakeResult
StatementAttachment = EmailIntakeResult
PSD2BankStreamer = PSD2OpenBankingClient
PSD2TransactionStream = PSD2BankProvider
InstantPaymentResult = InstantPaymentTransaction
PaymentType = PaymentSystem

__all__ = [
    # M25 Bulgarian PSD2 Open Banking
    "EmailStatementParser",
    "EmailIntakeResult",
    "ExtractedEmailPayload",
    "StatementAttachment",
    "PSD2OpenBankingClient",
    "PSD2BankProvider",
    "PSD2BankStreamer",
    "PSD2TransactionStream",
    "SEPABiseraInstantAdapter",
    "InstantPaymentTransaction",
    "PaymentSystem",
    "InstantPaymentResult",
    "PaymentType",
    "BankFeedGuard",
    "BankFeedItem",
    "BankFeedStatus",
    "ReconciliationSummary",
    "OpenBankingPISPAggregator",
    "PaymentInitiationRequest",
    "PaymentInitiationResult",
    # M83 CEE & EU Open Banking PISP/AISP Expansion
    "CEEOpenBankingAggregator",
    "CEEBankCode",
    "CEEBankProfile",
    "CEECountry",
    "CEECurrency",
    "CEEApiEnvironment",
    "CEEConsentToken",
    "CEEAccountBalance",
    "CEETransaction",
    "CEEPaymentResult",
    "CEEAggregatedBalance",
    "CEEPaymentBatchResult",
    "PIISPStatus",
    "CEE_BANK_REGISTRY",
    "validate_iban_cee",
    "validate_polish_nip",
    "validate_romanian_cif",
    "validate_greek_afm",
]
