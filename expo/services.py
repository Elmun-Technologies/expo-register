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

from datetime import timedelta

from django.utils import timezone

from . import simulation, telegram
from .models import Booth, Camera, ExpoVisitor, TrackingEvent, VisitAlert


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

    # Telegram orqali xavfsizlik xodimlarini xabardor qilish
    telegram.notify_new_visitor(visitor)

    return alert


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


def _zone_camera(zone):
    camera = Camera.objects.filter(is_enabled=True, zone__iexact=zone).first()
    if camera:
        return camera
    return Camera.objects.filter(is_enabled=True).first()


def _booth_for_zone(zone):
    return Booth.objects.filter(zone__iexact=zone).first()
