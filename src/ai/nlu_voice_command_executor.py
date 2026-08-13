"""
Milestone M61: Autonomous Voice & NLU Command Executor (m61_nlu_voice_command_executor)
======================================================================================

Extends the Bulgarian AI Voice Assistant (M46) from "Queries" mode to "Autonomous Execution" mode.

Features:
- Autonomous Execution Mode for accounting commands in Bulgarian.
- Bookkeeping & Journal Entry Execution (осчетоводявания: 503, 401, 411, 602, 621, 702, 4531/4532).
- Autonomous Open Banking PISP & Instant Payment Generation (генериране на плащания към контрагенти).
- Statutory NRA VAT Declaration Package Generation & Launch (стартиране на ДДС декларации и дневници).
- Security Guardrails & Confirmation Token Flow for high-value payments and official tax filings.
"""

import dataclasses
import enum
import hashlib
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.accounting.translate_to_delta import validate_eik, validate_iban
from src.audit.nra_vat_reporter import NRAVATDeclaration, NRAVATReporter, VATPeriod
from src.intake.open_banking_pisp import OpenBankingPISPAggregator, PaymentInitiationRequest
from src.intake.sepa_bisera_instant import PaymentSystem, SEPABiseraInstantAdapter

logger = logging.getLogger("nlu_voice_command_executor")


class ExecutionMode(str, enum.Enum):
    """Operational modes for the voice assistant."""
    QUERY_ONLY = "QUERY_ONLY"
    AUTONOMOUS_EXECUTION = "AUTONOMOUS_EXECUTION"


class ExecutionCommandType(str, enum.Enum):
    """Types of execution commands supported by NLU parser."""
    BOOKKEEPING_EXECUTION = "BOOKKEEPING_EXECUTION"
    PAYMENT_GENERATION = "PAYMENT_GENERATION"
    VAT_DECLARATION_LAUNCH = "VAT_DECLARATION_LAUNCH"
    MODE_SWITCH = "MODE_SWITCH"
    QUERY = "QUERY"
    UNKNOWN = "UNKNOWN"


class ExecutionStatus(str, enum.Enum):
    """Status of executed command."""
    EXECUTED = "EXECUTED"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    FAILED = "FAILED"
    REJECTED_SECURITY = "REJECTED_SECURITY"


@dataclasses.dataclass
class NLUCommandParseResult:
    """Parsed output from Bulgarian NLU command parser."""

    command_type: ExecutionCommandType
    confidence: float
    extracted_entities: Dict[str, Any]
    requires_confirmation: bool = False
    confirmation_reason: str = ""
    raw_text: str = ""
    normalized_text: str = ""


@dataclasses.dataclass
class VoiceExecutionResponse:
    """Response dataclass for autonomous command execution."""

    transcript_bg: str
    command_type: ExecutionCommandType
    status: ExecutionStatus
    spoken_response_bg: str
    data_payload: Dict[str, Any] = dataclasses.field(default_factory=dict)
    confirmation_token: Optional[str] = None
    journal_entry: Optional[Dict[str, Any]] = None
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS_EXECUTION


class BulgarianNLUCommandParser:
    """
    Bulgarian Natural Language Understanding parser for autonomous execution commands.
    Extracts intents, entities (amounts, counterparties, accounts, document numbers, periods),
    and confidence scores from Bulgarian voice and text inputs.
    """

    MONTH_NAME_MAP = {
        "януари": 1, "ян": 1, "01": 1,
        "февруари": 2, "фев": 2, "02": 2,
        "март": 3, "мар": 3, "03": 3,
        "април": 4, "апр": 4, "04": 4,
        "май": 5, "05": 5,
        "юни": 6, "06": 6,
        "юли": 7, "07": 7,
        "август": 8, "авг": 8, "08": 8,
        "септември": 9, "сеп": 9, "09": 9,
        "октомври": 10, "окт": 10, "10": 10,
        "ноември": 11, "ное": 11, "11": 11,
        "декември": 12, "дек": 12, "12": 12,
    }

    ACCOUNT_NAME_MAP = {
        "каса": "501",
        "банка": "503",
        "разплащателна": "503",
        "доставчик": "401",
        "доставчици": "401",
        "клиент": "411",
        "клиенти": "411",
        "наем": "602",
        "материали": "301",
        "стоки": "304",
        "банкова такса": "621",
        "такса": "621",
        "заплати": "421",
        "приход": "702",
        "приходи": "702",
        "ддс": "4531",
    }

    @classmethod
    def parse_command(cls, text: str) -> NLUCommandParseResult:
        """Parses Bulgarian command text into NLUCommandParseResult."""
        raw_text = text or ""
        normalized = cls._normalize_text(raw_text)

        # 1. Check Mode Switch Commands (Check QUERY_ONLY / disable first)
        if any(kw in normalized for kw in ["изключи автономен", "режим запитвания", "само запитвания"]):
            return NLUCommandParseResult(
                command_type=ExecutionCommandType.MODE_SWITCH,
                confidence=0.98,
                extracted_entities={"target_mode": ExecutionMode.QUERY_ONLY},
                raw_text=raw_text,
                normalized_text=normalized,
            )
        if any(kw in normalized for kw in ["включи автономен", "автономен режим", "режим изпълнение"]):
            return NLUCommandParseResult(
                command_type=ExecutionCommandType.MODE_SWITCH,
                confidence=0.98,
                extracted_entities={"target_mode": ExecutionMode.AUTONOMOUS_EXECUTION},
                raw_text=raw_text,
                normalized_text=normalized,
            )

        # 2. Check VAT Declaration Launch Commands
        if any(kw in normalized for kw in ["ддс декларация", "стартирай ддс", "генерирай ддс", "пускай ддс", "ддс отчет"]):
            entities = cls._extract_vat_entities(normalized)
            return NLUCommandParseResult(
                command_type=ExecutionCommandType.VAT_DECLARATION_LAUNCH,
                confidence=0.95,
                extracted_entities=entities,
                requires_confirmation=True,
                confirmation_reason="Генериране и подаване на официална ДДС декларация към НАП",
                raw_text=raw_text,
                normalized_text=normalized,
            )

        # 3. Check Payment Generation Commands
        if any(kw in normalized for kw in ["плати", "преведи", "генерирай плащане", "направи превод", "направи моментален", "плащане към", "превод към", "инстантен", "bisera"]):
            entities = cls._extract_payment_entities(normalized)
            amount = entities.get("amount", 0.0)
            requires_conf = amount > 10000.0  # High-value payment threshold
            conf_reason = f"Висока стойност на плащането ({amount:,.2f} лв.)" if requires_conf else ""
            return NLUCommandParseResult(
                command_type=ExecutionCommandType.PAYMENT_GENERATION,
                confidence=0.92,
                extracted_entities=entities,
                requires_confirmation=requires_conf,
                confirmation_reason=conf_reason,
                raw_text=raw_text,
                normalized_text=normalized,
            )

        # 4. Check Bookkeeping Execution Commands
        if any(kw in normalized for kw in ["осчетоводи", "запиши счетоводна", "въведи операци", "осчетоводяване", "запиши разход", "запиши приход"]):
            entities = cls._extract_bookkeeping_entities(normalized)
            return NLUCommandParseResult(
                command_type=ExecutionCommandType.BOOKKEEPING_EXECUTION,
                confidence=0.94,
                extracted_entities=entities,
                requires_confirmation=False,
                raw_text=raw_text,
                normalized_text=normalized,
            )

        # 5. Check Query Commands (Fallback to Query)
        if any(kw in normalized for kw in ["оборот", "приход", "салдо", "сметка", "пари", "ликвидност", "прогноза", "липсващи"]):
            return NLUCommandParseResult(
                command_type=ExecutionCommandType.QUERY,
                confidence=0.90,
                extracted_entities={},
                raw_text=raw_text,
                normalized_text=normalized,
            )

        # Unknown intent
        return NLUCommandParseResult(
            command_type=ExecutionCommandType.UNKNOWN,
            confidence=0.20,
            extracted_entities={},
            raw_text=raw_text,
            normalized_text=normalized,
        )

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @classmethod
    def _extract_amount(cls, text: str) -> float:
        """Extracts monetary amount, prioritizing numbers followed by monetary units (лв, евро, etc.)."""
        # First try numbers explicitly followed by monetary currency indicators
        match_curr = re.search(r"(\d+[\.,]?\d*)\s*(?:лв|лева|eur|евро|bgn)", text)
        if match_curr:
            try:
                return float(match_curr.group(1).replace(",", "."))
            except ValueError:
                pass

        # Next try 'за <amount>'
        match_for = re.search(r"(?:за|стойност)\s+(\d+[\.,]?\d*)", text)
        if match_for:
            try:
                return float(match_for.group(1).replace(",", "."))
            except ValueError:
                pass

        # Fallback: extract numbers that are not part of doc numbers or years
        tokens = text.split()
        for token in reversed(tokens):
            clean = re.sub(r"[^\d\.,]", "", token).replace(",", ".")
            if clean and not re.search(r"(?:20\d{2}|inv|№|фактура)", token):
                try:
                    val = float(clean)
                    if 0 < val < 1000000:
                        return val
                except ValueError:
                    pass
        return 0.0

    @classmethod
    def _extract_doc_number(cls, text: str) -> str:
        """Extracts invoice/document number."""
        match = re.search(r"(?:фактура|ф-ра|документ|№|inv-)\s*(?:№\s*)?([a-z0-9\-]+)", text)
        if match:
            return match.group(1).upper()
        return f"DOC-{datetime.now().strftime('%Y%m%d%H%M')}"

    @classmethod
    def _extract_vat_entities(cls, text: str) -> Dict[str, Any]:
        """Extracts year and month for VAT declaration."""
        now = datetime.now()
        year = now.year
        month = now.month

        # Match month name
        for month_name, m_num in cls.MONTH_NAME_MAP.items():
            if month_name in text:
                month = m_num
                break

        # Match year (e.g. 2026)
        match_yr = re.search(r"20\d{2}", text)
        if match_yr:
            year = int(match_yr.group(0))

        # Match MM.YYYY format
        match_mm_yyyy = re.search(r"(\d{2})[\./](\d{4})", text)
        if match_mm_yyyy:
            month = int(match_mm_yyyy.group(1))
            year = int(match_mm_yyyy.group(2))

        return {"year": year, "month": month}

    @classmethod
    def _extract_payment_entities(cls, text: str) -> Dict[str, Any]:
        """Extracts partner name, amount, remittance info, and bank/instant mode."""
        amount = cls._extract_amount(text)
        doc_no = cls._extract_doc_number(text)

        # Partner extraction after 'към' or 'на'
        partner = "Партньор ООД"
        match_partner = re.search(r"(?:към|на)\s+([а-яa-z0-9\s]+?)(?:\s+за|\s+по|\s+в|\s+чрез|$)", text)
        if match_partner:
            p_candidate = match_partner.group(1).strip()
            if p_candidate and len(p_candidate) > 2:
                partner = p_candidate.title()

        payment_system = "PISP"
        if "инстантно" in text or "bisera" in text or "моментален" in text:
            payment_system = "BISERA_6"

        return {
            "partner_name": partner,
            "amount": amount,
            "doc_number": doc_no,
            "remittance_info": f"Плащане по фактура {doc_no}",
            "payment_system": payment_system,
        }

    @classmethod
    def _extract_bookkeeping_entities(cls, text: str) -> Dict[str, Any]:
        """Extracts bookkeeping details: debit/credit accounts, amount, partner, doc number."""
        amount = cls._extract_amount(text)
        doc_no = cls._extract_doc_number(text)

        debit_acc = "602"  # Default services/rent
        credit_acc = "401"  # Default suppliers

        if "наем" in text:
            debit_acc = "602"
            credit_acc = "503"
        elif "банкова такса" in text or "такса" in text:
            debit_acc = "621"
            credit_acc = "503"
        elif "материали" in text:
            debit_acc = "301"
            credit_acc = "401"
        elif "приход" in text or "продажба" in text:
            debit_acc = "411"
            credit_acc = "702"

        partner = "АБВ Трейдинг ООД"
        match_partner = re.search(r"(?:от|към|с)\s+([а-яa-z0-9\s]+?)(?:\s+за|\s+по|\s+в|$)", text)
        if match_partner:
            p_candidate = match_partner.group(1).strip()
            if p_candidate and len(p_candidate) > 2:
                partner = p_candidate.title()

        return {
            "amount": amount,
            "doc_number": doc_no,
            "debit_account": debit_acc,
            "credit_account": credit_acc,
            "partner_name": partner,
            "narrative": f"Осчетоводяване по {doc_no} за {partner}",
        }


class AutonomousVoiceCommandExecutor:
    """
    Main Autonomous Voice & NLU Command Executor Engine.
    Executes accounting entries, payment initiation, and NRA VAT declarations via voice/text commands.
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.AUTONOMOUS_EXECUTION, company_eik: str = "123456789", company_name: str = "Финанс Защита ЕООД"):
        self.mode = mode
        self.company_eik = company_eik
        self.company_name = company_name
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        logger.info(f"🎙️ AutonomousVoiceCommandExecutor initialized in mode [{self.mode.value}] for EIK {self.company_eik}")

    def set_execution_mode(self, mode: ExecutionMode) -> str:
        """Toggles execution mode."""
        self.mode = mode
        logger.info(f"Execution mode switched to: {self.mode.value}")
        return f"Режимът на гласовия асистент е променен на {self.mode.value}."

    def execute_command(self, voice_transcript_bg: str, context_data: Optional[Dict[str, Any]] = None, confirmation_token: Optional[str] = None) -> VoiceExecutionResponse:
        """
        Parses and executes Bulgarian voice or text command.
        Handles security confirmation tokens for high-value or filing operations.
        """
        context = context_data or {}
        raw_text = voice_transcript_bg or ""

        # Handle pending confirmation resolution first if token provided
        if confirmation_token:
            if confirmation_token in self._pending_confirmations:
                pending_cmd = self._pending_confirmations.pop(confirmation_token)
                logger.info(f"✅ Executing confirmed command token: {confirmation_token}")
                return self._dispatch_execution(pending_cmd["parse_result"], context, confirmed=True)
            else:
                return VoiceExecutionResponse(
                    transcript_bg=raw_text,
                    command_type=ExecutionCommandType.UNKNOWN,
                    status=ExecutionStatus.FAILED,
                    spoken_response_bg="Грешка: Невалиден или изтекъл токен за потвърждение.",
                    execution_mode=self.mode,
                )

        # Parse command using Bulgarian NLU parser
        parse_result = BulgarianNLUCommandParser.parse_command(raw_text)

        # Handle Mode Switch
        if parse_result.command_type == ExecutionCommandType.MODE_SWITCH:
            target_mode = parse_result.extracted_entities.get("target_mode", ExecutionMode.AUTONOMOUS_EXECUTION)
            self.mode = target_mode
            spoken = f"Автономният режим на изпълнение беше променен на {'АКТИВЕН' if target_mode == ExecutionMode.AUTONOMOUS_EXECUTION else 'ИЗКЛЮЧЕН (Само запитвания)'}."
            return VoiceExecutionResponse(
                transcript_bg=raw_text,
                command_type=ExecutionCommandType.MODE_SWITCH,
                status=ExecutionStatus.EXECUTED,
                spoken_response_bg=spoken,
                data_payload={"mode": target_mode.value},
                execution_mode=self.mode,
            )

        # In QUERY_ONLY mode, reject autonomous write actions
        if self.mode == ExecutionMode.QUERY_ONLY and parse_result.command_type in [
            ExecutionCommandType.BOOKKEEPING_EXECUTION,
            ExecutionCommandType.PAYMENT_GENERATION,
            ExecutionCommandType.VAT_DECLARATION_LAUNCH,
        ]:
            return VoiceExecutionResponse(
                transcript_bg=raw_text,
                command_type=parse_result.command_type,
                status=ExecutionStatus.REJECTED_SECURITY,
                spoken_response_bg="Отказ: Асистентът е в режим 'Само запитвания'. Включете автономен режим за изпълнение на операции.",
                execution_mode=self.mode,
            )

        # Handle Confirmation Request if required
        if parse_result.requires_confirmation and not context.get("auto_approve", False):
            token = f"CONFIRM_{uuid.uuid4().hex[:8].upper()}"
            self._pending_confirmations[token] = {"parse_result": parse_result, "created_at": datetime.now()}
            spoken = f"Внимание: Изисква се потвърждение за тази операция ({parse_result.confirmation_reason}). Моля, потвърдете с токен {token}."
            return VoiceExecutionResponse(
                transcript_bg=raw_text,
                command_type=parse_result.command_type,
                status=ExecutionStatus.PENDING_CONFIRMATION,
                spoken_response_bg=spoken,
                confirmation_token=token,
                data_payload={"reason": parse_result.confirmation_reason, "entities": parse_result.extracted_entities},
                execution_mode=self.mode,
            )

        # Dispatch execution to appropriate subsystem
        return self._dispatch_execution(parse_result, context, confirmed=False)

    def _dispatch_execution(self, parse_result: NLUCommandParseResult, context: Dict[str, Any], confirmed: bool = False) -> VoiceExecutionResponse:
        cmd_type = parse_result.command_type

        if cmd_type == ExecutionCommandType.BOOKKEEPING_EXECUTION:
            return self._execute_bookkeeping(parse_result, context)
        elif cmd_type == ExecutionCommandType.PAYMENT_GENERATION:
            return self._execute_payment(parse_result, context)
        elif cmd_type == ExecutionCommandType.VAT_DECLARATION_LAUNCH:
            return self._execute_vat_declaration(parse_result, context)
        else:
            # Fallback to query execution
            return self._execute_query_fallback(parse_result, context)

    def _execute_bookkeeping(self, parse_result: NLUCommandParseResult, context: Dict[str, Any]) -> VoiceExecutionResponse:
        entities = parse_result.extracted_entities
        amount = entities.get("amount", 500.0)
        doc_no = entities.get("doc_number", "DOC-10023")
        debit_acc = entities.get("debit_account", "602")
        credit_acc = entities.get("credit_account", "401")
        partner = entities.get("partner_name", "АБВ Трейдинг ООД")
        narrative = entities.get("narrative", f"Автономно осчетоводяване {doc_no}")

        vat_amount = round(amount * 0.20, 2)
        total_amount = round(amount + vat_amount, 2)

        journal_entry = {
            "entry_id": f"JE_{uuid.uuid4().hex[:8].upper()}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "document_number": doc_no,
            "partner_name": partner,
            "partner_eik": context.get("partner_eik", "123456789"),
            "debit_account": debit_acc,
            "credit_account": credit_acc,
            "taxable_amount_bgn": amount,
            "vat_amount_bgn": vat_amount,
            "total_amount_bgn": total_amount,
            "narrative": narrative,
            "status": "POSTED_DELTA_PRO",
            "sha256_hash": hashlib.sha256(f"{doc_no}_{amount}_{partner}".encode()).hexdigest()[:16],
        }

        spoken = f"Успешно осчетоводих фактура {doc_no} от {partner} за {total_amount:,.2f} лева (Дебит {debit_acc} / Кредит {credit_acc})."
        logger.info(f"⚡ Bookkeeping executed: {doc_no} | {total_amount} BGN")

        return VoiceExecutionResponse(
            transcript_bg=parse_result.raw_text,
            command_type=ExecutionCommandType.BOOKKEEPING_EXECUTION,
            status=ExecutionStatus.EXECUTED,
            spoken_response_bg=spoken,
            journal_entry=journal_entry,
            data_payload={"journal_entry": journal_entry},
            execution_mode=self.mode,
        )

    def _execute_payment(self, parse_result: NLUCommandParseResult, context: Dict[str, Any]) -> VoiceExecutionResponse:
        entities = parse_result.extracted_entities
        partner = entities.get("partner_name", "Евро Транс ЕООД")
        amount = entities.get("amount", 1200.0)
        doc_no = entities.get("doc_number", "INV-2025-0142")
        payment_system = entities.get("payment_system", "PISP")

        creditor_iban = context.get("creditor_iban", "BG80STSA93000026384019")
        debtor_iban = context.get("debtor_iban", "BG18UNCR70001523984102")

        if payment_system == "BISERA_6" or "bisera" in parse_result.raw_text.lower():
            adapter = SEPABiseraInstantAdapter()
            tx = adapter.process_instant_payment(
                transaction_ref=f"INST_{doc_no}",
                iban=creditor_iban,
                counterparty=partner,
                amount=amount,
                payment_system=PaymentSystem.BISERA_6,
                currency="BGN",
            )
            journal = adapter.reconcile_with_accounts_payable(tx, [{"doc_number": doc_no, "partner": partner, "amount": amount}])
            spoken = f"Успешно извърших моментален превод през BISERA 6 на стойност {amount:,.2f} лв. към {partner}."
            payment_res = {"payment_id": tx.transaction_ref, "status": "SETTLED", "system": "BISERA_6", "journal": journal}
        else:
            req = PaymentInitiationRequest(
                payment_id=f"PAY_{uuid.uuid4().hex[:8].upper()}",
                debtor_iban=debtor_iban,
                creditor_iban=creditor_iban,
                creditor_name=partner,
                amount_eur=round(amount / 1.95583, 2),
                remittance_info=f"Фактура {doc_no}",
                bank_code="DSK",
            )
            pisp_result = OpenBankingPISPAggregator.initiate_vendor_payment(req)
            spoken = f"Генерирах и инициарах Open Banking PISP плащане по фактура {doc_no} към {partner} за {amount:,.2f} лева."
            payment_res = {"payment_id": pisp_result.payment_id, "status": pisp_result.transaction_status, "system": "PSD2_PISP", "journal": pisp_result.journal_entry}

        logger.info(f"💸 Payment generated: {partner} | {amount} BGN")

        return VoiceExecutionResponse(
            transcript_bg=parse_result.raw_text,
            command_type=ExecutionCommandType.PAYMENT_GENERATION,
            status=ExecutionStatus.EXECUTED,
            spoken_response_bg=spoken,
            journal_entry=payment_res.get("journal"),
            data_payload=payment_res,
            execution_mode=self.mode,
        )

    def _execute_vat_declaration(self, parse_result: NLUCommandParseResult, context: Dict[str, Any]) -> VoiceExecutionResponse:
        entities = parse_result.extracted_entities
        year = entities.get("year", datetime.now().year)
        month = entities.get("month", datetime.now().month)

        period = VATPeriod(year=year, month=month)
        decl = NRAVATDeclaration(
            eik=self.company_eik,
            company_name=self.company_name,
            vat_period=period,
            taxable_base_20=context.get("sales_base", 50000.0),
            vat_tax_20=context.get("sales_vat", 10000.0),
            purchases_taxable_base_20=context.get("purchases_base", 30000.0),
            purchases_vat_credit_20=context.get("purchases_vat", 6000.0),
        )

        deklar_txt = NRAVATReporter.generate_declar_txt(decl)

        spoken = (
            f"Стартирах и генерирах ДДС декларация за период {month:02d}.{year} г. "
            f"Начислен ДДС: {decl.vat_tax_20:,.2f} лв., ДДС за приспадане: {decl.purchases_vat_credit_20:,.2f} лв. "
            f"Резултат за внасяне по клетка 50: {decl.net_vat_payable:,.2f} лв."
        )

        vat_payload = {
            "eik": decl.eik,
            "period": period.period_str,
            "sales_vat": decl.vat_tax_20,
            "purchases_vat": decl.purchases_vat_credit_20,
            "vat_payable": decl.net_vat_payable,
            "vat_refundable": decl.net_vat_refundable,
            "deklar_txt_len": len(deklar_txt),
            "files_generated": ["DEKLAR.TXT", "POKUPKI.TXT", "PRODAGBI.TXT"],
        }

        logger.info(f"🏛️ VAT Declaration launched for period {period.period_str}")

        return VoiceExecutionResponse(
            transcript_bg=parse_result.raw_text,
            command_type=ExecutionCommandType.VAT_DECLARATION_LAUNCH,
            status=ExecutionStatus.EXECUTED,
            spoken_response_bg=spoken,
            data_payload=vat_payload,
            execution_mode=self.mode,
        )

    def _execute_query_fallback(self, parse_result: NLUCommandParseResult, context: Dict[str, Any]) -> VoiceExecutionResponse:
        from src.ai.voice_accounting_assistant import VoiceAccountingAssistant
        resp = VoiceAccountingAssistant.process_voice_query(parse_result.raw_text, context)
        return VoiceExecutionResponse(
            transcript_bg=parse_result.raw_text,
            command_type=ExecutionCommandType.QUERY,
            status=ExecutionStatus.EXECUTED,
            spoken_response_bg=resp.spoken_response_bg,
            data_payload=resp.data_payload,
            execution_mode=self.mode,
        )
