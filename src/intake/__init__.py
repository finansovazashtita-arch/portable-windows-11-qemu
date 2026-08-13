"""
Intake Package.
"""

from src.intake.bank_feed_guard import BankFeedGuard, BankFeedItem, BankFeedStatus, ReconciliationSummary
from src.intake.email_parser import EmailStatementParser, IMAPStatementFetcher
from src.intake.psd2_openbanking import PSD2BankProvider, PSD2OpenBankingClient
from src.intake.sepa_bisera_instant import InstantPaymentTransaction, SEPABiseraInstantAdapter

# Backward compatibility aliases
EmailStatementFetcher = IMAPStatementFetcher
PSD2BankType = PSD2BankProvider

__all__ = [
    "EmailStatementParser",
    "IMAPStatementFetcher",
    "EmailStatementFetcher",
    "PSD2OpenBankingClient",
    "PSD2BankProvider",
    "PSD2BankType",
    "SEPABiseraInstantAdapter",
    "InstantPaymentTransaction",
    "BankFeedGuard",
    "BankFeedItem",
    "BankFeedStatus",
    "ReconciliationSummary",
]
