import base64
import csv
import io
import json
import time

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from events.views import get_dashboard_type

from . import analytics, services, simulation
from .forms import KioskCheckinForm
from .models import Booth, Camera, ExpoVisitor, TrackingEvent, VisitAlert


def is_admin(user):
    # Admin / superuser — to'liq huquq
    return user.is_authenticated and (
        user.is_superuser or getattr(user, "role", "") == "ADMIN"
    )


def is_security(user):
    # Xavfsizlik xodimi — monitoring panelini ko'radi
    return user.is_authenticated and getattr(user, "role", "") == "SECURITY"


def can_monitor(user):
    return is_admin(user) or is_security(user)


# ==========================================================
# KIOSK — mehmon kirishi (ochiq ekran)
# ==========================================================

def kiosk(request):
    lang = request.GET.get("lang", "uz")
    if lang not in ("uz", "ru"):
        lang = "uz"

    created_visitor = None

    if request.method == "POST":
        form = KioskCheckinForm(request.POST, lang=lang)
        if form.is_valid():
            visitor = form.save(commit=False)
            visitor.sim_seed = simulation.stable_seed(
                visitor.badge_token.hex
            )
            visitor.planned_path = simulation.build_visitor_path(visitor)
            visitor.save()

            services.start_tracking(visitor)
            created_visitor = visitor
            form = KioskCheckinForm(lang=lang)
    else:
        form = KioskCheckinForm(lang=lang)

    booth_count = Booth.objects.count()

    return render(
        request,
        "expo/kiosk.html",
        {
            "form": form,
            "lang": lang,
            "created_visitor": created_visitor,
            "booth_count": booth_count,
        },
    )


# ==========================================================
# MONITORING — xavfsizlik paneli
# ==========================================================

@login_required
def monitor(request):
    if not can_monitor(request.user):
        messages.error(request, "Ushbu sahifaga kirish huquqi yo'q.")
        return redirect("dashboard_home")

    overview = analytics.expo_overview()
    cameras = Camera.objects.filter(is_enabled=True)
    zones = simulation.EXPO_ZONES

    return render(
        request,
        "expo/monitor.html",
        {
            "overview": overview,
            "cameras": cameras,
            "zones": zones,
            "dashboard_type": get_dashboard_type(request.user),
        },
    )


@login_required
def monitor_live_api(request):
    """Monitoring paneli uchun jonli JSON (AJAX polling)."""
    if not can_monitor(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)

    alerts = [
        {
            "id": a.id,
            "level": a.level,
            "message": a.message,
            "created_at": timezone_fmt(a.created_at),
        }
        for a in VisitAlert.objects.select_related("visitor")[:20]
    ]

    active_visitors = [
        {
            "id": v.id,
            "name": v.full_name,
            "company": v.company,
            "purpose": v.get_purpose_display(),
            "current_zone": v.current_zone,
            "minutes_inside": v.minutes_inside,
            "check_in_at": timezone_fmt(v.check_in_at),
        }
        for v in ExpoVisitor.objects.filter(status=ExpoVisitor.Status.ACTIVE)
    ]

    cameras = [
        {
            "id": c.id,
            "name": c.name,
            "zone": c.zone,
            "is_online": c.is_online,
            "mode": c.mode,
        }
        for c in Camera.objects.filter(is_enabled=True)
    ]

    return JsonResponse(
        {
            "overview": analytics.expo_overview(),
            "alerts": alerts,
            "active_visitors": active_visitors,
            "cameras": cameras,
        }
    )


def timezone_fmt(dt):
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(dt.timestamp()))


# ==========================================================
# API: simulyatsiya / kuzatuv
# ==========================================================

@login_required
def api_advance(request, visitor_id):
    if not can_monitor(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)

    visitor = get_object_or_404(ExpoVisitor, pk=visitor_id)
    zone = services.advance_tracking(visitor)

    return JsonResponse(
        {
            "ok": True,
            "visitor_id": visitor.id,
            "zone": zone,
            "status": visitor.status,
        }
    )


@login_required
def api_visitor_path(request, visitor_id):
    visitor = get_object_or_404(ExpoVisitor, pk=visitor_id)
    path = list(visitor.planned_path or [])
    events = [
        {
            "zone": e.zone,
            "kind": e.kind,
            "detected_at": timezone_fmt(e.detected_at),
        }
        for e in visitor.tracking_events.all()
    ]
    return JsonResponse(
        {
            "visitor": {
                "id": visitor.id,
                "name": visitor.full_name,
                "company": visitor.company,
                "status": visitor.status,
                "check_in_at": timezone_fmt(visitor.check_in_at),
                "minutes_inside": visitor.minutes_inside,
            },
            "path": path,
            "events": events,
        }
    )


# ==========================================================
# Visitors va stend analitikasi
# ==========================================================

@login_required
def visitors_list(request):
    if not can_monitor(request.user):
        messages.error(request, "Ushbu sahifaga kirish huquqi yo'q.")
        return redirect("dashboard_home")

    visitors = ExpoVisitor.objects.select_related().all()[:200]
    return render(
        request,
        "expo/visitors.html",
        {
            "visitors": visitors,
            "dashboard_type": get_dashboard_type(request.user),
        },
    )


@login_required
def visitor_detail(request, visitor_id):
    visitor = get_object_or_404(ExpoVisitor, pk=visitor_id)

    # Stend egasi (organizer) faqat o'z stendiga kelgan mehmonni ko'radi
    if not can_monitor(request.user):
        owns = Booth.objects.filter(owner=request.user)
        hit = visitor.tracking_events.filter(booth__in=owns).exists()
        if not hit:
            messages.error(request, "Ushbu mehmon sizning stendingizga kelmagan.")
            return redirect("expo_analytics")

    return render(
        request,
        "expo/visitor_detail.html",
        {
            "visitor": visitor,
            "events": visitor.tracking_events.all(),
            "dashboard_type": get_dashboard_type(request.user),
        },
    )


# ==========================================================
# Devices — kameralar va stendlar
# ==========================================================

@login_required
def devices(request):
    if not is_admin(request.user):
        messages.error(request, "Ushbu sahifaga kirish huquqi yo'q.")
        return redirect("dashboard_home")

    cameras = Camera.objects.all()
    booths = Booth.objects.all()
    return render(
        request,
        "expo/devices.html",
        {
            "cameras": cameras,
            "booths": booths,
            "dashboard_type": get_dashboard_type(request.user),
        },
    )


# ==========================================================
# Stend (Booth) analitikasi — stend egalari uchun
# ==========================================================

@login_required
def booth_analytics(request):
    user = request.user
    booths = Booth.objects.all()

    if not is_admin(user):
        # Stend egasi faqat o'z stendini ko'radi
        booths = booths.filter(owner=user)

    stats = [analytics.booth_summary(b) for b in booths.order_by("booth_number")]

    if is_admin(user):
        # Admin uchun eng qiziq stendlar reytingi
        stats.sort(key=lambda r: -r["unique_visitors"])

    return render(
        request,
        "expo/booth_analytics.html",
        {
            "stats": stats,
            "dashboard_type": get_dashboard_type(request.user),
        },
    )


@login_required
def api_booth_stats(request, booth_id):
    booth = get_object_or_404(Booth, pk=booth_id)
    s = analytics.booth_summary(booth)
    return JsonResponse(
        {
            "booth": booth.name,
            "booth_number": booth.booth_number,
            "visits": s["visits"],
            "unique_visitors": s["unique_visitors"],
            "avg_dwell_min": s["avg_dwell_min"],
        }
    )


# ==========================================================
# BADGE — mehmon kartochkasi (QR bilan chop etish uchun)
# ==========================================================

def _badge_qr_data_uri(visitor):
    """Mehmon kartochkasi uchun QR kod (base64 PNG)."""
    payload = (
        f"Expo Visitor\nName: {visitor.full_name}\n"
        f"Badge: {visitor.badge_token.hex[:12].upper()}\n"
        f"Company: {visitor.company or '-'}\n"
    )
    qr = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


@login_required
def visitor_badge(request, visitor_id):
    """Mehmon kartochkasini ko'rsatish (chop etish ekrani)."""
    visitor = get_object_or_404(ExpoVisitor, pk=visitor_id)
    if not can_monitor(request.user):
        owns = Booth.objects.filter(owner=request.user)
        hit = visitor.tracking_events.filter(booth__in=owns).exists()
        if not hit:
            messages.error(request, "Ushbu mehmon sizning stendingizga kelmagan.")
            return redirect("expo_analytics")

    return render(
        request,
        "expo/badge.html",
        {
            "visitor": visitor,
            "qr_data_uri": _badge_qr_data_uri(visitor),
        },
    )


# ==========================================================
# CSV EXPORT — Excel uchun
# ==========================================================

@login_required
def visitors_export_csv(request):
    if not can_monitor(request.user):
        messages.error(request, "Ushbu sahifaga kirish huquqi yo'q.")
        return redirect("dashboard_home")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="expo_visitors.csv"'
    response.write("\ufeff")  # BOM — Excel o'zbekcha harflarni to'g'ri ochishi uchun

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Ism", "Familiya", "Kompaniya", "Maqsad",
        "Telefon", "Email", "Holat", "Kirish vaqti", "Chiqish vaqti",
        "Ichkaridagi daqiqalar", "Oxirgi zona",
    ])

    for v in ExpoVisitor.objects.order_by("-check_in_at"):
        writer.writerow([
            v.id,
            v.first_name,
            v.last_name,
            v.company,
            v.get_purpose_display(),
            v.phone,
            v.email,
            "Ichkarida" if v.is_active else "Chiqib ketdi",
            timezone_fmt(v.check_in_at),
            timezone_fmt(v.check_out_at) if v.check_out_at else "",
            v.minutes_inside,
            v.current_zone,
        ])

    return response

