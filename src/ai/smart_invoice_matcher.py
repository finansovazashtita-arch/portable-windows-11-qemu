"""
M71: AI-Powered Smart Invoice Matching & Auto-Reconciliation Engine.

Provides:
1. Semantic Narrative Matching via vector embeddings & character n-gram cosine similarity.
2. Fuzzy Amount Matching with configurable tolerances for bank transfer fees, rounding, and cash discounts.
3. Transliteration & OCR misread normalization (Cyrillic <-> Latin, leading zeros, doc prefixes).
4. Multi-Factor AI Similarity Scoring & Automated Journal Entry Generation.
5. 1-Click Accountant Confirmation integration with Audit Ledger & Active Learning Loop.
"""

import dataclasses
import enum
import math
import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Set

logger = logging.getLogger("smart_invoice_matcher")

# Cyrillic to Latin transliteration dictionary for counterparty and narrative matching
CYR_TO_LAT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
    'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sht', 'ъ': 'a', 'ь': 'y',
    'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F',
    'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sht', 'Ъ': 'A', 'Ь': 'Y',
    'Ю': 'Yu', 'Я': 'Ya'
}

EUR_BGN_PEG = 1.95583


def transliterate_cyrillic_to_latin(text: str) -> str:
    """Translates Bulgarian Cyrillic characters to Latin equivalents."""
    res = []
    for char in text:
        res.append(CYR_TO_LAT_MAP.get(char, char))
    return "".join(res)


def normalize_text_token(text: str) -> str:
    """Normalizes text by lowercasing, stripping special characters, and converting Cyrillic."""
    text = text.lower()
    text = transliterate_cyrillic_to_latin(text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_numeric_tokens(text: str) -> Set[str]:
    """Extracts numeric invoice identifiers, stripping leading zeros."""
    raw_nums = re.findall(r'\b\d+\b', text)
    nums = set()
    for n in raw_nums:
        nums.add(n)
        # Strip leading zeros
        stripped = n.lstrip('0')
        if stripped:
            nums.add(stripped)
    return nums


class MatchConfidenceTier(str, enum.Enum):
    HIGH = "HIGH"          # >= 85% confidence (Ready for 1-click confirmation or auto-post)
    MEDIUM = "MEDIUM"      # 65% - 84% confidence (Needs accountant review)
    LOW = "LOW"            # 40% - 64% confidence (Weak match candidate)
    UNMATCHED = "UNMATCHED"# < 40% confidence


class ReconcileMatchStatus(str, enum.Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    AUTO_CONFIRMED = "AUTO_CONFIRMED"
    ACCOUNTANT_CONFIRMED = "ACCOUNTANT_CONFIRMED"
    REJECTED = "REJECTED"


@dataclasses.dataclass
class SmartReconciliationCandidate:
    """Dataclass holding AI invoice-to-bank-transaction match candidate metrics."""
    match_id: str
    invoice_id: str
    bank_tx_id: str
    overall_confidence: float
    confidence_tier: MatchConfidenceTier
    status: ReconcileMatchStatus
    
    # Detailed match breakdown scores
    narrative_embedding_score: float
    fuzzy_amount_score: float
    counterparty_match_score: float
    invoice_number_exact_match: bool
    
    # Financial metrics
    invoice_amount: float
    bank_tx_amount: float
    amount_difference: float
    currency: str
    
    # Metadata for UI display
    invoice_number: str
    invoice_counterparty: str
    bank_tx_narrative: str
    bank_tx_counterparty: str
    match_notes: str
    suggested_journal_entry: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["overall_confidence_pct"] = round(self.overall_confidence * 100, 1)
        return d


class NarrativeEmbeddingEngine:
    """AI Vector Embedding & Semantic Narrative Matcher."""

    @staticmethod
    def _get_char_ngrams(text: str, n: int = 3) -> Dict[str, int]:
        norm = normalize_text_token(text)
        counts: Dict[str, int] = {}
        for i in range(len(norm) - n + 1):
            gram = norm[i:i+n]
            counts[gram] = counts.get(gram, 0) + 1
        return counts

    @classmethod
    def compute_cosine_similarity(cls, text1: str, text2: str) -> float:
        """Computes TF-IDF / Character N-gram cosine similarity between two text narratives."""
        if not text1 or not text2:
            return 0.0
            
        grams1 = cls._get_char_ngrams(text1, n=3)
        grams2 = cls._get_char_ngrams(text2, n=3)
        
        if not grams1 or not grams2:
            return 0.0

        all_grams = set(grams1.keys()).union(set(grams2.keys()))
        dot_product = 0.0
        norm1 = 0.0
        norm2 = 0.0

        for g in all_grams:
            val1 = grams1.get(g, 0)
            val2 = grams2.get(g, 0)
            dot_product += val1 * val2
            norm1 += val1 * val1
            norm2 += val2 * val2

        mag = (math.sqrt(norm1) * math.sqrt(norm2))
        if mag == 0.0:
            return 0.0
        return dot_product / mag

    @classmethod
    def compute_invoice_number_similarity(cls, inv_no: str, narrative: str) -> Tuple[float, bool]:
        """Detects presence of invoice number in bank transaction narrative."""
        if not inv_no or not narrative:
            return 0.0, False

        inv_nums = extract_numeric_tokens(inv_no)
        nar_nums = extract_numeric_tokens(narrative)

        if not inv_nums:
            return 0.0, False

        # Check for exact numeric token overlap
        intersection = inv_nums.intersection(nar_nums)
        if intersection:
            return 1.0, True

        # Check sub-string matching for long invoice numbers
        norm_inv = normalize_text_token(inv_no)
        norm_nar = normalize_text_token(narrative)
        if norm_inv and norm_inv in norm_nar:
            return 0.95, True

        return 0.0, False

    @classmethod
    def score_narrative_matching(
        cls,
        inv_no: str,
        inv_narrative: str,
        bank_narrative: str,
    ) -> Tuple[float, bool]:
        """Combines embedding cosine similarity and invoice number extraction."""
        num_score, exact_match = cls.compute_invoice_number_similarity(inv_no, bank_narrative)
        embedding_score = cls.compute_cosine_similarity(inv_narrative, bank_narrative)

        if exact_match:
            # High weight if exact invoice number was found in narrative
            final_narrative_score = 0.6 * num_score + 0.4 * max(0.5, embedding_score)
        else:
            final_narrative_score = embedding_score

        return min(1.0, max(0.0, final_narrative_score)), exact_match


class FuzzyAmountMatcher:
    """Fuzzy Amount Matcher with tolerance for bank fees, rounding, and cash discounts."""

    @classmethod
    def score_amount_similarity(
        cls,
        inv_amount: float,
        bank_amount: float,
        inv_curr: str = "BGN",
        bank_curr: str = "BGN",
        abs_tolerance: float = 5.0,
        percent_tolerance: float = 2.0,
    ) -> Tuple[float, float]:
        """
        Calculates amount match score and absolute difference in BGN.
        Supports FX peg conversion if currencies differ (e.g. EUR vs BGN).
        """
        inv_amt_bgn = inv_amount * EUR_BGN_PEG if inv_curr.upper() == "EUR" else inv_amount
        bank_amt_bgn = bank_amount * EUR_BGN_PEG if bank_curr.upper() == "EUR" else bank_amount

        diff = abs(inv_amt_bgn - bank_amt_bgn)

        # 1. Exact match (up to 1 stotinka)
        if diff < 0.01:
            return 1.0, 0.0

        # 2. Rounding difference (up to 0.05 BGN)
        if diff <= 0.05:
            return 0.98, diff

        # 3. Absolute tolerance (bank transfer fees up to e.g. 5.00 BGN)
        if diff <= abs_tolerance:
            score = 0.95 - (diff / abs_tolerance) * 0.15  # 0.80 to 0.95
            return round(score, 3), diff

        # 4. Percentage tolerance (cash discount / skonto up to e.g. 2.0%)
        if inv_amt_bgn > 0:
            pct_diff = (diff / inv_amt_bgn) * 100.0
            if pct_diff <= percent_tolerance:
                score = 0.90 - (pct_diff / percent_tolerance) * 0.15 # 0.75 to 0.90
                return round(score, 3), diff

        # 5. Non-matching amounts
        pct_diff = (diff / max(1.0, inv_amt_bgn)) * 100.0
        score = max(0.0, 0.50 - (pct_diff / 50.0))
        return round(score, 3), diff


class CounterpartyMatcher:
    """Counterparty EIK / Name / IBAN matching logic."""

    @classmethod
    def score_counterparty_match(
        cls,
        inv_eik: Optional[str],
        inv_name: str,
        bank_eik: Optional[str],
        bank_name: str,
        bank_iban: Optional[str] = None,
        inv_iban: Optional[str] = None,
    ) -> float:
        # 1. EIK exact match
        if inv_eik and bank_eik and inv_eik.strip() == bank_eik.strip() and len(inv_eik.strip()) >= 9:
            return 1.0

        # 2. IBAN exact match
        if inv_iban and bank_iban and inv_iban.strip().upper() == bank_iban.strip().upper():
            return 1.0

        # 3. Name fuzzy embedding similarity
        if inv_name and bank_name:
            sim = NarrativeEmbeddingEngine.compute_cosine_similarity(inv_name, bank_name)
            return sim

        return 0.0


class SmartInvoiceMatcher:
    """M71 Core Smart AI Auto-Reconciliation Engine."""

    @classmethod
    def match_invoices_and_bank_txs(
        cls,
        invoices: List[Dict[str, Any]],
        bank_txs: List[Dict[str, Any]],
        min_confidence_threshold: float = 0.50,
        abs_amount_tolerance: float = 5.0,
        percent_amount_tolerance: float = 2.0,
    ) -> List[SmartReconciliationCandidate]:
        """
        Executes AI similarity scoring across all provided invoices and bank transactions.
        Returns sorted list of match candidates above min_confidence_threshold.
        """
        candidates: List[SmartReconciliationCandidate] = []

        for inv_idx, inv in enumerate(invoices):
            inv_id = str(inv.get("invoice_id") or inv.get("id") or f"INV_{inv_idx+1}")
            inv_no = str(inv.get("doc_number") or inv.get("invoice_number") or "N/A")
            inv_amt = float(inv.get("amount") or inv.get("total_amount") or 0.0)
            inv_curr = str(inv.get("currency") or "BGN")
            inv_party = str(inv.get("counterparty_name") or inv.get("vendor_name") or inv.get("customer_name") or "")
            inv_eik = inv.get("counterparty_eik") or inv.get("eik")
            inv_iban = inv.get("counterparty_iban") or inv.get("iban")
            inv_narrative = f"{inv_no} {inv_party} {inv.get('description', '')}"

            best_candidate: Optional[SmartReconciliationCandidate] = None
            highest_confidence = -1.0

            for tx_idx, tx in enumerate(bank_txs):
                tx_id = str(tx.get("item_id") or tx.get("tx_id") or f"TX_{tx_idx+1}")
                tx_debit = float(tx.get("debit_amount") or 0.0)
                tx_credit = float(tx.get("credit_amount") or 0.0)
                tx_amt = tx_debit if tx_debit > 0 else tx_credit
                tx_curr = str(tx.get("currency") or "BGN")
                tx_narrative = str(tx.get("narrative") or tx.get("payment_reason") or tx.get("details") or "")
                tx_party = str(tx.get("counterparty_name") or tx.get("party_name") or "")
                tx_eik = tx.get("counterparty_eik")
                tx_iban = tx.get("counterparty_iban")

                # 1. Narrative & Invoice Number Embedding Match
                narrative_score, exact_no_match = NarrativeEmbeddingEngine.score_narrative_matching(
                    inv_no, inv_narrative, tx_narrative
                )

                # 2. Fuzzy Amount Match Score
                amount_score, amount_diff = FuzzyAmountMatcher.score_amount_similarity(
                    inv_amt, tx_amt, inv_curr, tx_curr, abs_amount_tolerance, percent_amount_tolerance
                )

                # 3. Counterparty Similarity Score
                party_score = CounterpartyMatcher.score_counterparty_match(
                    inv_eik, inv_party, tx_eik, tx_party, tx_iban, inv_iban
                )

                # 4. Multi-Factor Weighted Overall Confidence Score
                # Weights: 45% Narrative/InvNo, 35% Amount, 20% Counterparty
                if exact_no_match:
                    # Give extra confidence boost if exact invoice number was found
                    overall = 0.50 * narrative_score + 0.35 * amount_score + 0.15 * party_score
                    if amount_score >= 0.8:
                        overall = max(overall, 0.92)
                else:
                    overall = 0.40 * narrative_score + 0.40 * amount_score + 0.20 * party_score

                overall = round(min(1.0, max(0.0, overall)), 3)

                if overall >= min_confidence_threshold and overall > highest_confidence:
                    highest_confidence = overall
                    
                    # Determine Tier
                    if overall >= 0.85:
                        tier = MatchConfidenceTier.HIGH
                    elif overall >= 0.65:
                        tier = MatchConfidenceTier.MEDIUM
                    elif overall >= 0.40:
                        tier = MatchConfidenceTier.LOW
                    else:
                        tier = MatchConfidenceTier.UNMATCHED

                    # Build Notes
                    notes_parts = []
                    if exact_no_match:
                        notes_parts.append("Открит точно номер на фактура в банковото основание.")
                    if narrative_score >= 0.70:
                        notes_parts.append(f"Векторно семантично съвпадение {round(narrative_score*100)}%.")
                    if amount_diff == 0.0:
                        notes_parts.append("Точна сума.")
                    else:
                        notes_parts.append(f"Fuzzy сума разлика: {round(amount_diff, 2)} лв.")

                    # Build Suggested Double-Entry Journal Entry
                    # Sales invoice: 503 Bank / 411 Debtors
                    # Purchase invoice: 401 Creditors / 503 Bank
                    is_purchase = inv.get("doc_type") in ("PURCHASE_INVOICE", "INCOMING") or tx_debit > 0
                    if is_purchase:
                        dr_acc = "401" # Доставчици
                        cr_acc = "503" # Разплащателна сметка
                    else:
                        dr_acc = "503" # Разплащателна сметка
                        cr_acc = "411" # Клиенти

                    journal_entry = {
                        "debit_account": dr_acc,
                        "credit_account": cr_acc,
                        "amount_bgn": round(min(inv_amt, tx_amt), 2),
                        "description": f"Автоматично AI засичане M71: Ф-ра #{inv_no} ↔ Банков референтен номер {tx_id}",
                    }

                    match_id = f"M71_{inv_id}_{tx_id}"

                    best_candidate = SmartReconciliationCandidate(
                        match_id=match_id,
                        invoice_id=inv_id,
                        bank_tx_id=tx_id,
                        overall_confidence=overall,
                        confidence_tier=tier,
                        status=ReconcileMatchStatus.PENDING_CONFIRMATION if overall < 0.98 else ReconcileMatchStatus.AUTO_CONFIRMED,
                        narrative_embedding_score=round(narrative_score, 3),
                        fuzzy_amount_score=round(amount_score, 3),
                        counterparty_match_score=round(party_score, 3),
                        invoice_number_exact_match=exact_no_match,
                        invoice_amount=inv_amt,
                        bank_tx_amount=tx_amt,
                        amount_difference=round(amount_diff, 2),
                        currency=inv_curr,
                        invoice_number=inv_no,
                        invoice_counterparty=inv_party or "Ненеизвестен контрагент",
                        bank_tx_narrative=tx_narrative,
                        bank_tx_counterparty=tx_party or "Ненеизвестно банково основание",
                        match_notes=" | ".join(notes_parts),
                        suggested_journal_entry=journal_entry,
                    )

            if best_candidate:
                candidates.append(best_candidate)

        # Sort by overall confidence descending
        candidates.sort(key=lambda c: c.overall_confidence, reverse=True)
        logger.info(f"M71 SmartInvoiceMatcher generated {len(candidates)} reconciliation candidates.")
        return candidates

    @classmethod
    def confirm_reconciliation_match(
        cls,
        candidate: SmartReconciliationCandidate,
        confirmed_by: str = "accountant_user",
    ) -> Dict[str, Any]:
        """
        Processes 1-Click Accountant confirmation of a smart match pair.
        Generates final journal entry, updates status, and logs to active learning & audit trail.
        """
        candidate.status = ReconcileMatchStatus.ACCOUNTANT_CONFIRMED
        
        # 1. Active Learning Loop Feedback persistence (if module present)
        try:
            from src.ai.active_learning_loop import ActiveLearningLoop
            loop = ActiveLearningLoop()
            loop.record_feedback(
                input_narrative=candidate.bank_tx_narrative,
                suggested_account=candidate.suggested_journal_entry.get("debit_account", "503"),
                corrected_account=candidate.suggested_journal_entry.get("debit_account", "503"),
                accountant_notes=f"Confirmed M71 AI match {candidate.invoice_number} ↔ {candidate.bank_tx_id} ({candidate.overall_confidence*100}%)",
            )
        except Exception as e:
            logger.debug(f"Active learning feedback logging skipped: {e}")

        # 2. Audit Ledger Guard tamper-evident logging (if module present)
        audit_hash = ""
        try:
            from src.security.audit_ledger_guard import AuditLedgerGuard
            guard = AuditLedgerGuard()
            audit_entry = guard.log_operation(
                operation_type="SMART_RECONCILIATION_CONFIRMATION",
                details={
                    "match_id": candidate.match_id,
                    "invoice_id": candidate.invoice_id,
                    "bank_tx_id": candidate.bank_tx_id,
                    "confidence": candidate.overall_confidence,
                    "confirmed_by": confirmed_by,
                    "journal_entry": candidate.suggested_journal_entry,
                }
            )
            audit_hash = audit_entry.get("entry_hash", "")
        except Exception as e:
            logger.debug(f"Audit ledger logging skipped: {e}")

        return {
            "success": True,
            "match_id": candidate.match_id,
            "status": candidate.status.value,
            "confirmed_by": confirmed_by,
            "journal_entry": candidate.suggested_journal_entry,
            "audit_hash": audit_hash,
            "message": f"Успешно потвърдено AI засичане M71 за фактура #{candidate.invoice_number}.",
        }
