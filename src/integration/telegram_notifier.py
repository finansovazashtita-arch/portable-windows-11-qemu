"""
Mobile Notifications & Telegram Bot Guard Module.

Sends instant real-time alerts to Telegram channels / mobile apps when:
- High/Critical risk AI fraud anomalies are detected
- HA Cluster failover is triggered between macmini nodes
- Nightly backup or QEMU VM reconciliation failures occur
"""

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("telegram_notifier")


class TelegramNotifier:
    """Sends real-time mobile and Telegram bot alerts for accounting anomalies."""

    BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
    CHAT_ID_ENV = "TELEGRAM_CHAT_ID"

    @classmethod
    def get_credentials(cls) -> Tuple[Optional[str], Optional[str]]:
        bot_token = os.environ.get(cls.BOT_TOKEN_ENV, "dummy_bot_token")
        chat_id = os.environ.get(cls.CHAT_ID_ENV, "dummy_chat_id")
        return bot_token, chat_id

    @classmethod
    def send_alert(cls, message: str, parse_mode: str = "Markdown") -> bool:
        """Sends text message to Telegram Bot API with offline fallback."""
        bot_token, chat_id = cls.get_credentials()

        if not bot_token or bot_token == "dummy_bot_token" or not chat_id or chat_id == "dummy_chat_id":
            logger.info(f"📲 [TELEGRAM ALERT (OFFLINE SIMULATION)]:\n{message}")
            return True

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": parse_mode}).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    logger.info("✅ Telegram notification sent successfully.")
                    return True
        except Exception as e:
            logger.warning(f"Failed to send Telegram alert: {e}. Falling back to logging.")

        logger.info(f"📲 [TELEGRAM ALERT (FALLBACK)]:\n{message}")
        return False

    @classmethod
    def send_fraud_alert(cls, risk_level: str, risk_score: float, flags: list, tx: Dict[str, Any]) -> bool:
        """Formats and dispatches high-priority fraud alert."""
        counterparty = tx.get("counterparty_name", "Неизвестен")
        amount = float(tx.get("debit_amount", 0.0)) or float(tx.get("credit_amount", 0.0))
        doc_no = tx.get("document_number", "N/A")

        msg = (
            f"🚨 *FinansProtect СИГНАЛ ЗА ИЗМАМА / АНОМАЛИЯ*\n\n"
            f"• *Ниво на риск:* `{risk_level}` (Оценка: {risk_score*100:.1f}%)\n"
            f"• *Контрагент:* {counterparty}\n"
            f"• *Сума:* €{amount:.2f}\n"
            f"• *Документ №:* `{doc_no}`\n"
            f"• *Открити флагове:* {', '.join(flags) if flags else 'Няма'}\n\n"
            f"🛑 *Действие:* Транзакцията е временно БЛОКИРАНА за ръчна проверка от главен счетоводител!"
        )
        return cls.send_alert(msg)

    @classmethod
    def send_cluster_alert(cls, event: str, leader_node: str, leader_host: str) -> bool:
        """Formats and dispatches HA cluster failover notification."""
        msg = (
            f"🌐 *HA КЛЪСТЕР ИЗВЕСТИЕ: {event}*\n\n"
            f"• *Нов Активен Лидер:* `{leader_node}`\n"
            f"• *IP Адрес:* `{leader_host}`\n"
            f"• *Статус:* Автоматичният failover пренасочи входящия трафик успешно."
        )
        return cls.send_alert(msg)
