"""
Intake Package.
"""

from src.intake.bank_feed_guard import BankFeedGuard, BankFeedItem, BankFeedStatus, ReconciliationSummary
from src.intake.email_parser import EmailIntakeResult, EmailStatementParser
from src.intake.open_banking_pisp import OpenBankingPISPAggregator, PaymentInitiationRequest, PaymentInitiationResult
from src.intake.psd2_openbanking import PSD2BankProvider, PSD2OpenBankingClient
from src.intake.sepa_bisera_instant import InstantPaymentTransaction, PaymentSystem, SEPABiseraInstantAdapter

# Backward compatibility aliases
ExtractedEmailPayload = EmailIntakeResult
StatementAttachment = EmailIntakeResult
PSD2BankStreamer = PSD2OpenBankingClient
PSD2TransactionStream = PSD2BankProvider
InstantPaymentResult = InstantPaymentTransaction
PaymentType = PaymentSystem

__all__ = [
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
]
