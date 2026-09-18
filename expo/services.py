"""
Kuzatuv xizmati: mehmon ro'yxatdan o'tishi bilan TIZIM ISHGA TUSHADI.

Oqim:
1. Kioskda ism/familiya kiritiladi -> ExpoVisitor yaratiladi.
2. "Ro'yxatga olindi + kuzatuv boshlandi" xabari (VisitAlert) yoziladi.
3. Kuzatuv kameralari (Camera) mavjud bo'lsa, mehmonni kuzatish
   boshlanadi: SIMULATION rejimida virtual harakat yo'li yoziladi,
   LIVE rejimda Hikvision kamerasi uchun so'rov jo'natiladi.
4. Har bir zona/stend oldida TrackingEvent qayd etiladi va analitika
   uchun saqlanadi.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from . import simulation, sms, telegram
from .models import Booth, Camera, ExpoVisitor, TrackingEvent, VisitAlert

logger = logging.getLogger(__name__)


def assign_sim(visitor):
    """Simulyatsiya uchun deterministik yo'l tayyorlash."""
    if not visitor.sim_seed:
        seed = simulation.stable_seed(visitor.badge_token.hex)
        visitor.sim_seed = seed
        visitor.planned_path = simulation.build_visitor_path(visitor)
        visitor.save(update_fields=["sim_seed", "planned_path"])
    return visitor


def start_tracking(visitor):
    """
    Mehmon uchun kuzatuvni boshlash. Yangi ro'yxatdan o'tganda chaqiriladi.
    """
    visitor = assign_sim(visitor)

    alert = VisitAlert.objects.create(
        visitor=visitor,
        level=VisitAlert.Level.SUCCESS,
        message=f"{visitor.full_name} ro'yxatdan o'tdi — kuzatuv boshlandi",
    )

    zones = list(visitor.planned_path or []) or [simulation.EXPO_ZONES[0]]

    first_camera = Camera.objects.filter(is_enabled=True).first()

    TrackingEvent.objects.create(
        visitor=visitor,
        camera=first_camera,
        zone=zones[0],
        kind=TrackingEvent.Kind.SEEN,
        detected_at=timezone.now(),
        note="Kuzatuv boshlandi",
    )

    if first_camera:
        first_camera.is_online = True
        first_camera.last_seen = timezone.now()
        first_camera.save(update_fields=["is_online", "last_seen"])
        # LIVE kamerani kirish nuqtasiga (preset 1) burish —
        # kuzatuv kameralari "aynan shu mijozni kuzatish"ni boshlaydi.
        if first_camera.mode == Camera.Mode.LIVE:
            try:
                from . import hikvision

                hikvision.goto_preset(first_camera, preset_id=1)
            except Exception:
                # Kameraga ulanishda muammo bo'lsa kuzatuv to'xtamaydi.
                logger.warning("LIVE kamera PTZ sozlab bo'lmadi.", exc_info=True)

    # Telegram orqali xavfsizlik xodimlarini xabardor qilish
    telegram.notify_new_visitor(visitor)

    # SMS orqali mehmonni xabardor qilish (telefon bo'lsa)
    sms.notify_visitor_sms(visitor)

    return alert


def auto_advance_all():
    """
    Barcha faol mehmonlar uchun vaqt bo'yicha avtomatik kuzatuv progressi.

    Har bir mehman o'z yo'lida (planned_path) yurydi. Oxirgi hodisadan
    beri ``DEMO_VISIT_STEP_MINUTES`` daqiqa o'tganda navbatdagi zonaga
    (kameraga) o'tadi. Yo'l tugab, vaqt o'tib ketsa — avtomatik chiqib
    ketadi.

    Background worker talab qilinmaydi: monitoring paneli har so'rovda
    shuni chaqiradi (DB o'qib, kerak bo'lganda yozadi).
    """
    from django.conf import settings

    step_minutes = getattr(settings, "DEMO_VISIT_STEP_MINUTES", 6)
    now = timezone.now()

    for visitor in ExpoVisitor.objects.filter(status=ExpoVisitor.Status.ACTIVE).iterator():
        try:
            _auto_advance_visitor(visitor, step_minutes, now)
        except Exception:  # noqa: BLE001
            logger.exception("Avtomatik kuzatuv xatosi (visitor %s)", visitor.pk)


def _auto_advance_visitor(visitor, step_minutes, now):
    """Bitta mehmon uchun vaqt bo'yicha progress (avtomatik)."""
    if not visitor.is_active:
        return

    last_event = visitor.tracking_events.order_by("-detected_at").first()
    last_at = last_event.detected_at if last_event else visitor.check_in_at

    step_seconds = step_minutes * 60
    if (now - last_at).total_seconds() < step_seconds:
        return

    steps = int((now - last_at).total_seconds() // step_seconds)
    for _ in range(min(steps, 20)):
        if not visitor.is_active:
            break
        advance_tracking(visitor)


def advance_tracking(visitor):
    """
    Mehmonni navbatdagi zonaga "ko'chirish" (simulyatsiya).

    Har chaqirilganda yo'ldagi keyingi nuqtaga o'tadi; tugaganda
    mehmon "chiqib ketdi" holatiga o'tkaziladi.
    """
    if not visitor.is_active:
        return None

    visitor = assign_sim(visitor)

    path = list(visitor.planned_path or [])
    # Har bir qadam (SEEN/ENTERED) bitta hodisa qo'shadi — ulardan
    # yo'lning qayerida ekanini aniqlaymiz.
    done = visitor.tracking_events.exclude(kind=TrackingEvent.Kind.LEFT).count()
    total = max(1, len(path))

    if done >= total or not path:
        return check_out(visitor)

    next_zone = path[done]
    camera = _zone_camera(next_zone)
    booth = _booth_for_zone(next_zone)

    TrackingEvent.objects.create(
        visitor=visitor,
        camera=camera,
        booth=booth,
        zone=next_zone,
        kind=TrackingEvent.Kind.ENTERED if booth else TrackingEvent.Kind.SEEN,
        detected_at=timezone.now(),
        note=f"{next_zone} — kuzatuvda",
    )

    visitor.current_zone = next_zone
    visitor.save(update_fields=["current_zone"])

    if camera:
        camera.is_online = True
        camera.last_seen = timezone.now()
        camera.save(update_fields=["is_online", "last_seen"])
        # LIVE kamerani mehmon joylashgan joyga burish —
        # "aynan shu mijoz kuzatilmoqda".
        if camera.mode == Camera.Mode.LIVE:
            try:
                from . import hikvision

                hikvision.goto_preset(camera, preset_id=1)
            except Exception:  # noqa: BLE001
                logger.warning("LIVE kamera PTZ sozlab bo'lmadi.", exc_info=True)

    visit_alert_on_detection(visitor, next_zone)
    return next_zone


def check_out(visitor):
    """Mehmonning expodan chiqib ketishini qayd etish."""
    if not visitor.is_active:
        return None

    visitor.status = ExpoVisitor.Status.LEFT
    visitor.check_out_at = timezone.now()
    visitor.save(update_fields=["status", "check_out_at"])

    TrackingEvent.objects.create(
        visitor=visitor,
        zone="Chiqish (Exit)",
        kind=TrackingEvent.Kind.LEFT,
        detected_at=timezone.now(),
        note="Expo hududidan chiqdi",
    )

    VisitAlert.objects.create(
        visitor=visitor,
        level=VisitAlert.Level.WARNING,
        message=f"{visitor.full_name} hududni tark etdi",
    )

    telegram.notify_visitor_left(visitor)

    return "Chiqish (Exit)"


def visit_alert_on_detection(visitor, zone):
    """Kamera mehmonni ko'rganida xabar yozish."""
    VisitAlert.objects.create(
        visitor=visitor,
        level=VisitAlert.Level.INFO,
        message=f"{visitor.full_name} — {zone}",
    )


def recognize_for_camera(camera, image_path=None):
    """
    Kamera kadridan mehmonni tanib olish (face recognition).

    Agar surat berilmasa va kamera LIVE bo'lsa, Hikvision'dan jonli
    snapshot olinadi; SIMULATION'da esa virtual kadr bo'ladi (bu holda
    haqiqiy tanib bo'lmaydi — yo'l bo'yicha "kutilayotgan" mehmon
    qaytariladi).

    Tanilgan mehmon uchun TrackingEvent (SEEN) yoziladi va qaytariladi:
        (visitor, confidence)
    """
    from . import face, hikvision

    # Kadr mavjud bo'lsa — chuqur tanish
    if image_path:
        visitor, confidence = face.match_visitor(image_path)
        if visitor:
            TrackingEvent.objects.create(
                visitor=visitor,
                camera=camera,
                zone=camera.zone,
                kind=TrackingEvent.Kind.SEEN,
                detected_at=timezone.now(),
                note=f"Kamera tanidi (confidence {confidence:.0f})",
            )
            return visitor, confidence
        return None, confidence

    # LIVE kamera — Hikvision snapshot
    if camera.mode == Camera.Mode.LIVE:
        try:
            data = hikvision.capture_snapshot(camera)
        except Exception:
            data = None
        if data:
            import tempfile, os
            fd, path = tempfile.mkstemp(suffix=".jpg")
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            try:
                visitor, confidence = face.match_visitor(path)
            finally:
                os.unlink(path)
            if visitor:
                TrackingEvent.objects.create(
                    visitor=visitor,
                    camera=camera,
                    zone=camera.zone,
                    kind=TrackingEvent.Kind.SEEN,
                    detected_at=timezone.now(),
                    note="Hikvision kadrdan tanidi",
                )
                return visitor, confidence
            return None, confidence

    return None, None


def _zone_camera(zone):
    camera = Camera.objects.filter(is_enabled=True, zone__iexact=zone).first()
    if camera:
        return camera
    return Camera.objects.filter(is_enabled=True).first()


def _booth_for_zone(zone):
    return Booth.objects.filter(zone__iexact=zone).first()
