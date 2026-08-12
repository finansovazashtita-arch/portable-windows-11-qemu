"""
Unit and Integration Tests for Automated Email Intake Parser.
"""

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import tempfile
import unittest

from src.intake.email_parser import EmailStatementParser, IMAPStatementFetcher


class TestEmailStatementParser(unittest.TestCase):
    """Test suite for EmailStatementParser."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.parser = EmailStatementParser(target_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_mime_email_with_pdf_attachment(self):
        msg = MIMEMultipart()
        msg["From"] = "bank@dsk.bg"
        msg["Subject"] = "Месечно извлечение - СТОРГОЗИЯ АД"
        msg["Date"] = "Wed, 01 Feb 2026 10:00:00 +0200"

        body = MIMEText("Уважаеми клиенти, приложено изпращаме вашето банково извлечение.")
        msg.attach(body)

        pdf_attachment = MIMEApplication(b"%PDF-1.4 DUMMY BANK STATEMENT DATA", _subtype="pdf")
        pdf_attachment.add_header("Content-Disposition", "attachment", filename="DSK_Statement_Jan2026.pdf")
        msg.attach(pdf_attachment)

        raw_bytes = msg.as_bytes()
        res = self.parser.parse_mime_bytes(raw_bytes, message_id="msg_unit_001")

        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(res.is_valid_statement)
        self.assertEqual(res.sender, "bank@dsk.bg")
        self.assertEqual(res.total_attachments, 1)
        self.assertIn("DSK_Statement_Jan2026.pdf", res.attachment_names)
        self.assertTrue(os.path.exists(res.attachment_paths[0]))

    def test_parse_mime_email_no_attachments(self):
        msg = MIMEMultipart()
        msg["From"] = "info@dsk.bg"
        msg["Subject"] = "Информационно съобщение"
        msg.attach(MIMEText("Няма приложени файлове."))

        raw_bytes = msg.as_bytes()
        res = self.parser.parse_mime_bytes(raw_bytes, message_id="msg_unit_002")

        self.assertEqual(res.status, "NO_ATTACHMENTS")
        self.assertFalse(res.is_valid_statement)
        self.assertEqual(res.total_attachments, 0)

    def test_imap_fetcher_missing_credentials_fallback(self):
        fetcher = IMAPStatementFetcher(username="", password="")
        results = fetcher.fetch_new_statements(self.parser)
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
