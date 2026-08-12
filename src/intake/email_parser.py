"""
Automated Email Intake Parser & IMAP Fetcher Module.

Supports parsing incoming MIME email messages, extracting PDF and ZIP attachments,
validating email senders and attachment integrity, and fetching new statements from IMAP/Gmail inboxes.
"""

import dataclasses
import email
from email.message import Message
import imaplib
import logging
import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("email_parser")


@dataclasses.dataclass
class EmailIntakeResult:
    """Result container for parsed email statement intake."""

    sender: str
    subject: str
    date: str
    message_id: str
    attachment_paths: List[str]
    attachment_names: List[str]
    total_attachments: int
    is_valid_statement: bool
    status: str  # "SUCCESS" | "NO_ATTACHMENTS" | "ERROR"
    error_message: Optional[str] = None


class EmailStatementParser:
    """Parses raw MIME email bytes or Message objects to extract statement attachments."""

    ALLOWED_EXTENSIONS = {".pdf", ".zip"}

    def __init__(self, target_dir: Optional[str] = None):
        self.target_dir = target_dir or tempfile.gettempdir()
        os.makedirs(self.target_dir, exist_ok=True)

    def parse_mime_bytes(self, raw_email_bytes: bytes, message_id: str = "msg_001") -> EmailIntakeResult:
        """Parses raw MIME email bytes and extracts PDF/ZIP statement attachments."""
        try:
            msg = email.message_from_bytes(raw_email_bytes)
            return self.parse_email_message(msg, message_id=message_id)
        except Exception as e:
            logger.error(f"Failed to parse MIME email bytes: {e}")
            return EmailIntakeResult(
                sender="unknown",
                subject="unknown",
                date="",
                message_id=message_id,
                attachment_paths=[],
                attachment_names=[],
                total_attachments=0,
                is_valid_statement=False,
                status="ERROR",
                error_message=str(e),
            )

    def parse_email_message(self, msg: Message, message_id: str = "msg_001") -> EmailIntakeResult:
        """Extracts sender, subject, date, and attachments from a python email.message.Message object."""
        sender = msg.get("From", "unknown@domain.com")
        subject = msg.get("Subject", "")
        date = msg.get("Date", "")

        saved_paths: List[str] = []
        saved_names: List[str] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                filename = part.get_filename()

                if filename and ("attachment" in content_disposition or "inline" in content_disposition):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in self.ALLOWED_EXTENSIONS:
                        clean_filename = f"{message_id}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)}"
                        out_path = os.path.join(self.target_dir, clean_filename)
                        payload = part.get_payload(decode=True)
                        if payload:
                            with open(out_path, "wb") as f:
                                f.write(payload)
                            saved_paths.append(out_path)
                            saved_names.append(filename)
        else:
            filename = msg.get_filename()
            if filename:
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.ALLOWED_EXTENSIONS:
                    clean_filename = f"{message_id}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)}"
                    out_path = os.path.join(self.target_dir, clean_filename)
                    payload = msg.get_payload(decode=True)
                    if payload:
                        with open(out_path, "wb") as f:
                            f.write(payload)
                        saved_paths.append(out_path)
                        saved_names.append(filename)

        status = "SUCCESS" if saved_paths else "NO_ATTACHMENTS"
        is_valid = bool(saved_paths)

        return EmailIntakeResult(
            sender=sender,
            subject=subject,
            date=date,
            message_id=message_id,
            attachment_paths=saved_paths,
            attachment_names=saved_names,
            total_attachments=len(saved_paths),
            is_valid_statement=is_valid,
            status=status,
        )


class IMAPStatementFetcher:
    """Fetches unread emails with statement attachments from an IMAP server."""

    def __init__(
        self,
        host: str = "imap.gmail.com",
        port: int = 993,
        username: str = "",
        password: str = "",
        mailbox: str = "INBOX",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mailbox = mailbox

    def fetch_new_statements(self, parser: EmailStatementParser) -> List[EmailIntakeResult]:
        """Connects to IMAP mailbox and fetches attachments from unread emails."""
        if not self.username or not self.password:
            logger.warning("IMAP credentials missing; skipping active IMAP poll.")
            return []

        results: List[EmailIntakeResult] = []
        try:
            client = imaplib.IMAP4_SSL(self.host, self.port)
            client.login(self.username, self.password)
            client.select(self.mailbox)

            status, data = client.search(None, "UNSEEN")
            if status != "OK" or not data or not data[0]:
                client.logout()
                return []

            msg_nums = data[0].split()
            for num in msg_nums:
                res_status, msg_data = client.fetch(num, "(RFC822)")
                if res_status == "OK" and msg_data and msg_data[0]:
                    raw_bytes = msg_data[0][1]
                    res = parser.parse_mime_bytes(raw_bytes, message_id=f"imap_{num.decode('utf-8')}")
                    results.append(res)

            client.logout()
        except Exception as e:
            logger.error(f"Failed to fetch emails via IMAP: {e}")

        return results
