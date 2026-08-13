"""
Unit and integration tests for Autonomous Voice & NLU Command Executor (Milestone M61).
"""

import unittest
from datetime import datetime

from src.ai.nlu_voice_command_executor import (
    AutonomousVoiceCommandExecutor,
    BulgarianNLUCommandParser,
    ExecutionCommandType,
    ExecutionMode,
    ExecutionStatus,
    VoiceExecutionResponse,
)
from src.ai.voice_accounting_assistant import VoiceAccountingAssistant, VoiceQueryType


class TestBulgarianNLUCommandParser(unittest.TestCase):
    """Test suite for Bulgarian NLU command parsing logic."""

    def test_parse_mode_switch_commands(self):
        res1 = BulgarianNLUCommandParser.parse_command("Включи автономен режим")
        self.assertEqual(res1.command_type, ExecutionCommandType.MODE_SWITCH)
        self.assertEqual(res1.extracted_entities.get("target_mode"), ExecutionMode.AUTONOMOUS_EXECUTION)

        res2 = BulgarianNLUCommandParser.parse_command("Изключи автономен режим и спри")
        self.assertEqual(res2.command_type, ExecutionCommandType.MODE_SWITCH)
        self.assertEqual(res2.extracted_entities.get("target_mode"), ExecutionMode.QUERY_ONLY)

    def test_parse_bookkeeping_commands(self):
        res = BulgarianNLUCommandParser.parse_command("Осчетоводи фактура 10023 от АБВ Трейдинг за 1500 лв")
        self.assertEqual(res.command_type, ExecutionCommandType.BOOKKEEPING_EXECUTION)
        self.assertEqual(res.extracted_entities.get("amount"), 1500.0)
        self.assertIn("10023", res.extracted_entities.get("doc_number"))

    def test_parse_payment_commands(self):
        res = BulgarianNLUCommandParser.parse_command("Плати фактура INV-2025-0142 към Евро Транс ЕООД за 1200 лв")
        self.assertEqual(res.command_type, ExecutionCommandType.PAYMENT_GENERATION)
        self.assertEqual(res.extracted_entities.get("amount"), 1200.0)
        self.assertIn("INV-2025-0142", res.extracted_entities.get("doc_number"))
        self.assertFalse(res.requires_confirmation)  # < 10000 BGN

        res_high = BulgarianNLUCommandParser.parse_command("Преведи 25000 лв към Стройком АД")
        self.assertEqual(res_high.command_type, ExecutionCommandType.PAYMENT_GENERATION)
        self.assertTrue(res_high.requires_confirmation)  # > 10000 BGN

    def test_parse_vat_declaration_commands(self):
        res = BulgarianNLUCommandParser.parse_command("Стартирай ДДС декларация за месец 01.2026 г.")
        self.assertEqual(res.command_type, ExecutionCommandType.VAT_DECLARATION_LAUNCH)
        self.assertEqual(res.extracted_entities.get("year"), 2026)
        self.assertEqual(res.extracted_entities.get("month"), 1)
        self.assertTrue(res.requires_confirmation)


class TestAutonomousVoiceCommandExecutor(unittest.TestCase):
    """Test suite for AutonomousVoiceCommandExecutor execution engine."""

    def setUp(self):
        self.executor = AutonomousVoiceCommandExecutor(company_eik="123456789")

    def test_execute_bookkeeping_command(self):
        res = self.executor.execute_command("Осчетоводи разход за наем 600 лв")
        self.assertEqual(res.status, ExecutionStatus.EXECUTED)
        self.assertEqual(res.command_type, ExecutionCommandType.BOOKKEEPING_EXECUTION)
        self.assertIn("720.00", res.spoken_response_bg)  # 600 BGN + 20% VAT
        self.assertIsNotNone(res.journal_entry)
        self.assertEqual(res.journal_entry.get("debit_account"), "602")

    def test_execute_pisp_payment_command(self):
        res = self.executor.execute_command("Плати фактура 102 към Евро Транс ЕООД за 800 лв")
        self.assertEqual(res.status, ExecutionStatus.EXECUTED)
        self.assertEqual(res.command_type, ExecutionCommandType.PAYMENT_GENERATION)
        self.assertIn("Open Banking PISP", res.spoken_response_bg)
        self.assertEqual(res.data_payload.get("status"), "ACCP")

    def test_execute_instant_bisera_payment(self):
        res = self.executor.execute_command("Направи моментален превод през BISERA 6 на стойност 3500 лв към Стройком АД")
        self.assertEqual(res.status, ExecutionStatus.EXECUTED)
        self.assertEqual(res.command_type, ExecutionCommandType.PAYMENT_GENERATION)
        self.assertIn("BISERA 6", res.spoken_response_bg)
        self.assertEqual(res.data_payload.get("system"), "BISERA_6")

    def test_execute_vat_declaration_with_confirmation(self):
        # Initial call requires confirmation
        res = self.executor.execute_command("Стартирай ДДС декларация за януари 2026")
        self.assertEqual(res.status, ExecutionStatus.PENDING_CONFIRMATION)
        self.assertIsNotNone(res.confirmation_token)

        # Confirming with token
        token = res.confirmation_token
        res_confirmed = self.executor.execute_command("", confirmation_token=token)
        self.assertEqual(res_confirmed.status, ExecutionStatus.EXECUTED)
        self.assertEqual(res_confirmed.command_type, ExecutionCommandType.VAT_DECLARATION_LAUNCH)
        self.assertIn("ДДС декларация за период 01.2026", res_confirmed.spoken_response_bg)

    def test_query_only_mode_security_rejection(self):
        self.executor.set_execution_mode(ExecutionMode.QUERY_ONLY)
        res = self.executor.execute_command("Плати фактура за 500 лв")
        self.assertEqual(res.status, ExecutionStatus.REJECTED_SECURITY)
        self.assertIn("Отказ", res.spoken_response_bg)


class TestVoiceAccountingAssistantIntegration(unittest.TestCase):
    """Integration test suite for VoiceAccountingAssistant M61 extensions."""

    def test_voice_assistant_bookkeeping_execution(self):
        res = VoiceAccountingAssistant.process_voice_query("Осчетоводи фактура 5504 за 1200 лв")
        self.assertEqual(res.query_type, VoiceQueryType.BOOKKEEPING_EXECUTION)
        self.assertEqual(res.execution_status, ExecutionStatus.EXECUTED.value)

    def test_voice_assistant_payment_generation(self):
        res = VoiceAccountingAssistant.process_voice_query("Плати 450 лв на АБВ Трейдинг")
        self.assertEqual(res.query_type, VoiceQueryType.PAYMENT_GENERATION)
        self.assertEqual(res.execution_status, ExecutionStatus.EXECUTED.value)

    def test_voice_assistant_legacy_query_preservation(self):
        res = VoiceAccountingAssistant.process_voice_query("Какъв е оборотът за днес?", {"turnover_eur": 5000.0})
        self.assertEqual(res.query_type, VoiceQueryType.TURNOVER_QUERY)
        self.assertIn("5,000.00 евро", res.spoken_response_bg)


if __name__ == "__main__":
    unittest.main()
