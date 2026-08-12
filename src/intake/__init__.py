"""
Automated Intake Package (Email, Cloudflare Worker, Webhooks).
"""

from src.intake.email_parser import EmailIntakeResult, EmailStatementParser, IMAPStatementFetcher

__all__ = ["EmailIntakeResult", "EmailStatementParser", "IMAPStatementFetcher"]
