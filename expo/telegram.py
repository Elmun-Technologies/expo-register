"""
Telegram xabarnomasi (O'zbekiston bozori uchun).

Bot tokeni va chat ID `.env` da beriladi:
    TELEGRAM_BOT_TOKEN=123456:ABC...
    TELEGRAM_CHAT_ID=-100123456789

Sozlanmagan bo'lsa, xabarlar faqat konsolga yoziladi.
"""

import logging
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _send_message(text):
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        logger.info("[Telegram] (sozlanmagan) %s", text)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
    ).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
            return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram xabari yuborilmadi: %r", exc)
        return False


def notify_new_visitor(visitor):
    """
    Yangi mehmon ro'yxatdan o'tganda xavfsizlik guruhiga xabar yuborish.
    """
    local_time = timezone.localtime(visitor.check_in_at)
    text = (
        "🚨 <b>Yangi mehmon ro'yxatdan o'tdi</b>\n\n"
        f"👤 <b>{visitor.full_name}</b>\n"
        f"🏢 Kompaniya: {visitor.company or '—'}\n"
        f"🎯 Maqsad: {visitor.get_purpose_display()}\n"
        f"🕒 Vaqt: {local_time.strftime('%d.%m.%Y %H:%M')}\n\n"
        "✅ Kuzatuv boshlandi."
    )
    return _send_message(text)


def notify_visitor_left(visitor):
    """Mehmon expodan chiqib ketganda xabar."""
    text = (
        "👋 <b>Mehmon hududni tark etdi</b>\n\n"
        f"👤 {visitor.full_name}\n"
        f"🏢 {visitor.company or '—'}\n"
        f"⏱️ Expo ichida: ~{visitor.minutes_inside} daqiqa"
    )
    return _send_message(text)
