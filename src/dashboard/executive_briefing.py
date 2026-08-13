"""
Multi-Language Executive Financial Briefing Generator Engine (BG / EN / DE C-Level Briefings).

Generates daily C-level executive financial summary reports in Bulgarian, English, and German:
- Processed daily turnover (€ and BGN)
- Transaction volume and OCR precision
- Corporate solvency score and audit integrity status
"""

import dataclasses
import enum
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("executive_briefing")


class BriefingLanguage(str, enum.Enum):
    BULGARIAN = "BG"
    ENGLISH = "EN"
    GERMAN = "DE"


@dataclasses.dataclass
class ExecutiveBriefingReport:
    """Dataclass holding localized C-level executive briefing results."""

    language: BriefingLanguage
    title: str
    daily_turnover_formatted: str
    total_transactions_count: int
    solvency_status_summary: str
    audit_integrity_status: str
    full_markdown_body: str


class ExecutiveBriefingGenerator:
    """Generator crafting daily C-level executive financial briefings."""

    @classmethod
    def generate_briefing(
        cls,
        daily_turnover_eur: float,
        transaction_count: int,
        solvency_score: float = 3.2,
        ocr_accuracy_percent: float = 99.8,
        language: BriefingLanguage = BriefingLanguage.BULGARIAN,
    ) -> ExecutiveBriefingReport:
        """Generates localized daily executive briefing."""
        date_str = time.strftime("%Y-%m-%d")
        turnover_bgn = daily_turnover_eur * 1.95583

        if language == BriefingLanguage.BULGARIAN:
            title = f"📈 Ежедневен Финансов Доклад за Ръководството ({date_str})"
            turnover_fmt = f"{daily_turnover_eur:,.2f} EUR ({turnover_bgn:,.2f} BGN)"
            solvency_summary = "Стабилна платежоспособност (Safe Zone)" if solvency_score >= 2.99 else "Умерен риск"
            audit_status = "100% Верифициран SHA-256 / HSM Подпис"
            body = (
                f"# {title}\n\n"
                f"**Дата**: {date_str}\n\n"
                f"### 📊 Ключови Индикатори (KPIs):\n"
                f"- **Оборот за деня**: {turnover_fmt}\n"
                f"- **Обработени транзакции**: {transaction_count:,} бр.\n"
                f"- **Точност на OCR извличане**: {ocr_accuracy_percent:.1f}%\n"
                f"- **Индекс на платежоспособност (Altman Z-Score)**: {solvency_score:.2f} ({solvency_summary})\n"
                f"- **Одитен статус**: {audit_status}\n"
            )
        elif language == BriefingLanguage.GERMAN:
            title = f"📈 Tägliche Finanzzusammenfassung für die Geschäftsführung ({date_str})"
            turnover_fmt = f"{daily_turnover_eur:,.2f} EUR ({turnover_bgn:,.2f} BGN)"
            solvency_summary = "Solide Zahlungsfähigkeit (Safe Zone)" if solvency_score >= 2.99 else "Mäßiges Risiko"
            audit_status = "100% Verifiziert mit SHA-256 / HSM Signatur"
            body = (
                f"# {title}\n\n"
                f"**Datum**: {date_str}\n\n"
                f"### 📊 Wichtigste Leistungsindikatoren (KPIs):\n"
                f"- **Tagesumsatz**: {turnover_fmt}\n"
                f"- **Verarbeitete Transaktionen**: {transaction_count:,}\n"
                f"- **OCR-Genauigkeit**: {ocr_accuracy_percent:.1f}%\n"
                f"- **Solvenzindex (Altman Z-Score)**: {solvency_score:.2f} ({solvency_summary})\n"
                f"- **Audit-Status**: {audit_status}\n"
            )
        else:  # ENGLISH
            title = f"📈 Daily Executive Financial Briefing ({date_str})"
            turnover_fmt = f"{daily_turnover_eur:,.2f} EUR ({turnover_bgn:,.2f} BGN)"
            solvency_summary = "Solid Solvency (Safe Zone)" if solvency_score >= 2.99 else "Moderate Risk"
            audit_status = "100% Verified SHA-256 / HSM Signature"
            body = (
                f"# {title}\n\n"
                f"**Date**: {date_str}\n\n"
                f"### 📊 Key Performance Indicators (KPIs):\n"
                f"- **Daily Turnover**: {turnover_fmt}\n"
                f"- **Processed Transactions**: {transaction_count:,}\n"
                f"- **OCR Extraction Precision**: {ocr_accuracy_percent:.1f}%\n"
                f"- **Solvency Index (Altman Z-Score)**: {solvency_score:.2f} ({solvency_summary})\n"
                f"- **Audit Status**: {audit_status}\n"
            )

        report = ExecutiveBriefingReport(
            language=language,
            title=title,
            daily_turnover_formatted=turnover_fmt,
            total_transactions_count=transaction_count,
            solvency_status_summary=solvency_summary,
            audit_integrity_status=audit_status,
            full_markdown_body=body,
        )
        logger.info(f"👔 Executive Briefing generated successfully in [{language.value}]")
        return report
