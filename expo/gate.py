"""
Darvoza (gate) xizmati — manager telefoni uchun QR / walk-in ro'yxat.

Bir yagona kirish yo'li: ``create_visitor_from_scan``.

U quyidagilarni bajaradi:
1. QR ichidagi ``Ticket ID`` (Eventify ro'yxat UUID si) yoki Expo badge
   kodini topadi va shu odamga bog'laydi;
2. QR topilmasa — manager kiritgan ism/familiya/kompaniya bilan
   joyida (walk-in) mehmon yaratadi;
3. Darhol kuzatuvni boshlaydi (kameralar + xabar + Telegram/SMS).
4. Offline navbatdan kelgan yozuvlar ``offline_id`` orqali idempotent
   qilinadi — bir xil yozuv ikki marta sinxronlanmaydi.
"""

import logging
import re
import uuid

from django.utils import timezone

from . import face, services
from .models import Booth, Camera, ExpoVisitor

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}"
    r"-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
)


def _extract_ticket_code(text):
    """QR matnidagi birinchi UUID ni qaytarish."""
    if not text:
        return None
    m = _UUID_RE.search(text)
    return m.group(0) if m else None


def _strings(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _find_registration(code):
    """Ticket UUID bo'yicha ro'yxatni topish."""
    if not code:
        return None
    from registrations.models import Registration

    return Registration.objects.filter(ticket_code=code).first()


def create_visitor_from_scan(payload):
    """
    Skaner yoki offline navbatdan kelgan payload dan ExpoVisitor yaratadi.

    Payload maydonlari:
        qr_text        — skanerlangan QR matni (ixtiyoriy)
        first_name     — ism (QR esiz bo'lsa)
        last_name      — familiya
        company        — kompaniya
        phone          — telefon
        purpose        — tashrif maqsadi (ExpoVisitor.Purpose)
        visit_type     — VISITOR / EXHIBITOR
        offline_id     — mijoz qurilmasida yaratilgan UUID
        photo_data     — surat (base64 data URL)

    Qaytaradi: (visitor, created, status, message)
        created  — yangi yaratildimi (True/False)
        status   — "ok" | "already" | "error"
        message  — foydalanuvchiga ko'rsatiladigan qisqa izoh
    """
    offline_id = payload.get("offline_id") or None

    # --------------------------------------------------
    # Idempotentlik: offline navbatdan yuborilgan yozuv
    # avval yaratilgan bo'lsa, uni qaytaramiz.
    # --------------------------------------------------
    if offline_id:
        try:
            offline_uuid = uuid.UUID(str(offline_id))
        except (ValueError, TypeError):
            offline_uuid = None
        if offline_uuid:
            existing = ExpoVisitor.objects.filter(offline_id=offline_uuid).first()
            if existing:
                return existing, False, "ok", "Offline yozuv allaqachon sinxronlangan"

    qr_text = _strings(payload, "qr_text", "qr", "ticket_code")
    ticket_code = _extract_ticket_code(qr_text)

    # --------------------------------------------------
    # 1) QR — Eventify ro'yxati (bot orqali ro'yxatdan o'tgan)
    # --------------------------------------------------
    registration = _find_registration(ticket_code) if ticket_code else None
    if registration:
        # Shu ro'yxat allaqachon ichkariga kiritilganmi?
        visitor = getattr(registration, "expo_visitor", None)
        if visitor:
            if visitor.is_active:
                return visitor, False, "already", "Bu mehmon allaqachon ichkarida"
            # Chiqib ketgan — qayta kirishga ruxsat (yangi sana bilan)
            visitor.status = ExpoVisitor.Status.ACTIVE
            visitor.check_in_at = timezone.now()
            visitor.check_out_at = None
            visitor.save(update_fields=["status", "check_in_at", "check_out_at"])
            services.start_tracking(visitor)
            return visitor, False, "ok", "Qayta kiritildi — kuzatuv yangilandi"

        user = registration.attendee
        first_name = user.first_name or _strings(payload, "first_name")
        last_name = user.last_name or _strings(payload, "last_name") or (user.username or "")
        company = _strings(payload, "company")
        phone = _strings(payload, "phone") or getattr(user, "phone_number", "")
        email = user.email or ""

        visitor = ExpoVisitor(
            first_name=first_name,
            last_name=last_name,
            company=company,
            phone=phone,
            email=email,
            purpose=_purpose(payload, ExpoVisitor.Purpose.BUSINESS),
            visit_type=_visit_type(payload),
            source=ExpoVisitor.Source.GATE_QR,
            registration=registration,
            offline_id=offline_uuid if 'offline_id' in payload else None,
            created_by=payload.get("created_by"),
        )
        visitor.save()

        _attach_photo(visitor, payload.get("photo_data"))
        visitor.face_hash = _face_hash(visitor)
        visitor.save(update_fields=["face_hash"]) if visitor.face_hash else None

        services.start_tracking(visitor)
        return visitor, True, "ok", "Ro'yxatdan topildi — kuzatuv boshlandi"

    # --------------------------------------------------
    # 2) Walk-in — QR yo'q, manager joyida ma'lumot kiritadi
    # --------------------------------------------------
    first_name = _strings(payload, "first_name")
    last_name = _strings(payload, "last_name")
    if not first_name or not last_name:
        return None, False, "error", "Ism va familiya kiritilishi shart"

    # Dublikat nazorati: xuddi shu ism-familiyali mehmon ichkarida bo'lsa
    existing = ExpoVisitor.objects.filter(
        first_name__iexact=first_name,
        last_name__iexact=last_name,
        status=ExpoVisitor.Status.ACTIVE,
    ).first()
    if existing:
        return existing, False, "already", "Bu mehmon allaqachon ichkarida"

    visitor = ExpoVisitor(
        first_name=first_name,
        last_name=last_name,
        company=_strings(payload, "company"),
        phone=_strings(payload, "phone"),
        purpose=_purpose(payload, ExpoVisitor.Purpose.BUSINESS),
        visit_type=_visit_type(payload),
        source=ExpoVisitor.Source.GATE_WALKIN,
        offline_id=offline_uuid if 'offline_id' in payload else None,
        created_by=payload.get("created_by"),
    )
    visitor.save()

    _attach_photo(visitor, payload.get("photo_data"))
    visitor.face_hash = _face_hash(visitor)
    visitor.save(update_fields=["face_hash"]) if visitor.face_hash else None

    services.start_tracking(visitor)
    return visitor, True, "ok", "Joyida ro'yxatga olindi — kuzatuv boshlandi"


def _attach_photo(visitor, photo_data):
    """base64 suratni mehmon photosiga yozish."""
    if not photo_data or "," not in str(photo_data):
        return
    from django.core.files.base import ContentFile
    import base64

    header, b64 = str(photo_data).split(",", 1)
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return
    ext = "png" if "png" in header else "jpg"
    visitor.photo.save(f"{uuid.uuid4().hex}.{ext}", ContentFile(raw), save=False)


def _face_hash(visitor):
    try:
        if visitor.photo and visitor.photo.path:
            return face.face_hash(visitor.photo.path)
    except Exception:
        return ""
    return ""


def _purpose(payload, default):
    value = (payload.get("purpose") or "").strip().upper()
    if value in ExpoVisitor.Purpose.values:
        return value
    mapping = {
        "BIZNES": ExpoVisitor.Purpose.BUSINESS,
        "BUSINESS": ExpoVisitor.Purpose.BUSINESS,
        "HAMKORLIK": ExpoVisitor.Purpose.PARTNERSHIP,
        "PARTNERSHIP": ExpoVisitor.Purpose.PARTNERSHIP,
        "INVESTOR": ExpoVisitor.Purpose.INVESTOR,
        "MEDIA": ExpoVisitor.Purpose.MEDIA,
        "MATBUOT": ExpoVisitor.Purpose.MEDIA,
        "STUDENT": ExpoVisitor.Purpose.STUDENT,
        "TALABA": ExpoVisitor.Purpose.STUDENT,
        "OTHER": ExpoVisitor.Purpose.OTHER,
        "BOShQA": ExpoVisitor.Purpose.OTHER,
    }
    return mapping.get(value, default)


def _visit_type(payload):
    value = (payload.get("visit_type") or "").strip().upper()
    if value in ExpoVisitor.VisitType.values:
        return value
    # "mehmon" so'zi yoki boshqasi
    if value in ("EKSPONENT", "EXHIBITOR", "EXPO", "PARTICIPANT"):
        return ExpoVisitor.VisitType.EXHIBITOR
    return ExpoVisitor.VisitType.VISITOR


def sync_offline_batch(entries):
    """
    Offline navbatdagi bir nechta yozuvni sinxronlash.

    ``entries`` — payload ro'yxati. Har biri uchun qaytadi:
        {"offline_id": ..., "status": "ok"|"already"|"error",
         "visitor_id": ..., "full_name": ...}
    """
    results = []
    for entry in entries:
        try:
            visitor, created, status, message = create_visitor_from_scan(entry)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Offline sinxronlashda xato")
            results.append({
                "offline_id": entry.get("offline_id"),
                "status": "error",
                "message": str(exc),
            })
            continue
        results.append({
            "offline_id": entry.get("offline_id"),
            "status": status,
            "created": created,
            "message": message,
            "visitor_id": getattr(visitor, "pk", None),
            "full_name": getattr(visitor, "full_name", ""),
        })
    return results
