"""
Expo analitikasi: stendlar uchun qiziqish statistikasi,
mehmonlar oqimi va kuzatuv natijalari.

Har bir stend egasi (booth owner) o'z stendi oldida nechta
mehmon bo'lgani, qancha vaqt turishgani va qaysi hududlar
eng faol ekanini ko'ra oladi.
"""

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncHour
from django.utils import timezone

from .models import Booth, Camera, ExpoVisitor, TrackingEvent


def booth_summary(booth):
    """Bitta stend uchun qisqa statistika."""
    events = TrackingEvent.objects.filter(booth=booth)
    visitors = ExpoVisitor.objects.filter(
        tracking_events__booth=booth,
    ).distinct()

    dwells = [
        v.minutes_inside
        for v in visitors
    ]

    return {
        "booth": booth,
        "visits": events.filter(kind=TrackingEvent.Kind.ENTERED).count(),
        "unique_visitors": visitors.count(),
        "avg_dwell_min": round(sum(dwells) / len(dwells)) if dwells else 0,
    }


def all_booth_stats():
    """Barcha stendlar bo'yicha to'liq statistika."""
    return [
        booth_summary(booth)
        for booth in Booth.objects.all().order_by("booth_number")
    ]


def expo_overview():
    """Monitoring panelining yuqori qismidagi umumiy ko'rsatkichlar."""
    now = timezone.now()

    active_visitors = ExpoVisitor.objects.filter(
        status=ExpoVisitor.Status.ACTIVE,
    ).count()

    total_today = ExpoVisitor.objects.filter(
        check_in_at__date=now.date(),
    ).count()

    cameras = Camera.objects.filter(is_enabled=True)
    cameras_online = cameras.filter(is_online=True).count()
    cameras_total = cameras.count()

    total_seen = TrackingEvent.objects.filter(
        kind=TrackingEvent.Kind.SEEN,
        detected_at__gte=now - timedelta(hours=24),
    ).count()

    return {
        "active_visitors": active_visitors,
        "total_today": total_today,
        "cameras_online": cameras_online,
        "cameras_total": cameras_total,
        "total_seen_24h": total_seen,
    }


def hourly_flow(chart_days=1):
    """Soatlik mehmon oqimi (diagramma uchun)."""
    since = timezone.now() - timedelta(days=chart_days)
    qs = (
        ExpoVisitor.objects.filter(check_in_at__gte=since)
        .annotate(hour=TruncHour("check_in_at"))
        .values("hour")
        .annotate(c=Count("id"))
        .order_by("hour")
    )
    labels, values = [], []
    for row in qs:
        labels.append(timezone.localtime(row["hour"]).strftime("%H:%M"))
        values.append(row["c"])
    return {"labels": labels, "values": values}


def zone_heatmap():
    """Zonalar bo'yicha shovqin ma'lumoti."""
    counts = defaultdict(int)
    for ev in TrackingEvent.objects.filter(
        kind__in=[TrackingEvent.Kind.SEEN, TrackingEvent.Kind.ENTERED],
    ):
        counts[ev.zone] += 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def booth_leaderboard():
    """Eng qiziq stendlar reytingi."""
    rows = []
    for booth in Booth.objects.all():
        visitors = ExpoVisitor.objects.filter(
            tracking_events__booth=booth,
        ).distinct().count()
        rows.append({"booth": booth, "visitors": visitors})
    rows.sort(key=lambda r: -r["visitors"])
    return rows
