"""
SMS xabarnoma — O'zbekiston uchun (Eskiz.uz / PlayMobile).

Eskiz.uz API:
    POST https://notify.eskiz.uz/api/auth/login
    POST https://notify.eskiz.uz/api/message/sms/send

Sozlamalar `.env` da:
    ESKIZ_EMAIL=...
    ESKIZ_PASSWORD=...
    ESKIZ_FROM=4546

Sozlanmagan bo'lsa, xabarlar konsolga yoziladi.
"""

import base64
import json
import logging
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_token():
    email = getattr(settings, "ESKIZ_EMAIL", "")
    password = getattr(settings, "ESKIZ_PASSWORD", "")
    if not email or not password:
        return None

    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        "https://notify.eskiz.uz/api/auth/login",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("token")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Eskiz login xatosi: %r", exc)
        return None


def send_sms(phone, text):
    """Telefon raqamiga SMS yuborish. Sozlanmagan bo'lsa False."""
    token = _get_token()
    if not token:
        logger.info("[SMS] (sozlanmagan) -> %s: %s", phone, text)
        return False

    from_number = getattr(settings, "ESKIZ_FROM", "4546")
    payload = json.dumps(
        {
            "mobile_phone": phone,
            "message": text,
            "from": from_number,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://notify.eskiz.uz/api/message/sms/send",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Eskiz SMS xatosi: %r", exc)
        return False


def notify_visitor_sms(visitor):
    """
    Mehmon ro'yxatdan o'tganda unga SMS yuborish (badge ma'lumoti bilan).
    Faqat telefon raqami bo'lsagina.
    """
    phone = (visitor.phone or "").strip()
    if not phone:
        return False

    text = (
        f"Expo: {visitor.full_name}, siz ro'yxatdan o'tdingiz! "
        f"Badge ID: {visitor.badge_token.hex[:8].upper()}. "
        "Yaxshi dam oling!"
    )
    return send_sms(phone, text)
