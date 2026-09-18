import base64
import csv
import io
import json
import logging
import time
import uuid

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from events.views import get_dashboard_type

from . import analytics, face, gate, services, simulation
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


def _save_visitor_photo(visitor, photo_data):
    """
    Veb-kameradan olingan base64 (data URL) suratni
    mehmon photosiga saqlash.
    """
    if not photo_data or "," not in photo_data:
        return False
    header, b64 = photo_data.split(",", 1)
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return False

    ext = "jpg"
    if "png" in header:
        ext = "png"
    visitor.photo.save(
        f"{uuid.uuid4().hex}.{ext}",
        ContentFile(raw),
        save=False,
    )
    return True


# ==========================================================
# KIOSK — mehmon kirishi (ochiq ekran)
# ==========================================================

def kiosk(request):
    lang = request.GET.get("lang", "uz")
    if lang not in ("uz", "ru"):
        lang = "uz"

    created_visitor = None
    duplicate = None
    duplicate_reason = ""

    if request.method == "POST":
        form = KioskCheckinForm(request.POST, lang=lang)
        if form.is_valid():
            visitor = form.save(commit=False)
            visitor.sim_seed = simulation.stable_seed(
                visitor.badge_token.hex
            )
            visitor.planned_path = simulation.build_visitor_path(visitor)

            # Veb-kameradan olingan suratni saqlash
            photo_data = form.cleaned_data.get("photo_data", "")
            if photo_data:
                _save_visitor_photo(visitor, photo_data)
                # Yuz izini hisoblash (dublikat nazorati uchun)
                try:
                    if visitor.photo:
                        visitor.face_hash = face.face_hash(visitor.photo.path)
                except Exception:
                    visitor.face_hash = ""

            visitor.save()

            # Dublikat nazorati — bir odam ikkinchi marta ro'yxatdan o'tmasin
            dup, reason = face.find_duplicate(visitor)
            if dup:
                duplicate = dup
                duplicate_reason = reason
                # Dublikat — bu yozuvni o'chirib, mavjudiga ishora qilamiz
                if visitor.photo:
                    visitor.photo.delete(save=False)
                visitor.delete()
                form = KioskCheckinForm(lang=lang)
            else:
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
            "duplicate": duplicate,
            "duplicate_reason": duplicate_reason,
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
            "snapshot_url": f"/expo/devices/camera/{c.id}/snapshot/",
        }
        for c in Camera.objects.filter(is_enabled=True)
    ]

    zone_data = analytics.zone_heatmap()

    return JsonResponse(
        {
            "overview": analytics.expo_overview(),
            "alerts": alerts,
            "active_visitors": active_visitors,
            "cameras": cameras,
            "zones": zone_data,
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

    visitors = ExpoVisitor.objects.select_related().all()

    # ------------------------------------------
    # QIDIRUV
    # ------------------------------------------
    search = request.GET.get("search", "").strip()
    if search.lower() == "none":
        search = ""
    if search:
        visitors = visitors.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(company__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
        )

    # ------------------------------------------
    # HOLAT FILTRI
    # ------------------------------------------
    status = request.GET.get("status", "").strip()
    if status == "active":
        visitors = visitors.filter(status=ExpoVisitor.Status.ACTIVE)
    elif status == "left":
        visitors = visitors.filter(status=ExpoVisitor.Status.LEFT)

    # ------------------------------------------
    # MAQSAD FILTRI
    # ------------------------------------------
    purpose = request.GET.get("purpose", "").strip()
    if purpose in ExpoVisitor.Purpose.values:
        visitors = visitors.filter(purpose=purpose)

    total = visitors.count()
    visitors = visitors[:300]

    return render(
        request,
        "expo/visitors.html",
        {
            "visitors": visitors,
            "total": total,
            "search": search,
            "current_status": status,
            "current_purpose": purpose,
            "purposes": ExpoVisitor.Purpose.choices,
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


@login_required
def camera_toggle(request, camera_id):
    """Kamerani yoqish / o'chirish (admin)."""
    if not is_admin(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)

    camera = get_object_or_404(Camera, pk=camera_id)
    camera.is_enabled = not camera.is_enabled
    camera.save(update_fields=["is_enabled"])
    return JsonResponse(
        {
            "ok": True,
            "camera_id": camera.id,
            "is_enabled": camera.is_enabled,
        }
    )


@login_required
def camera_snapshot(request, camera_id):
    """
    LIVE rejimdagi Hikvision kameradan jonli kadr (snapshot) olish.
    SIMULATION kamerada demo (virtual) kadr qaytariladi.
    """
    if not can_monitor(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)

    camera = get_object_or_404(Camera, pk=camera_id)

    from . import hikvision as hv

    try:
        data = hv.capture_snapshot(camera)
    except hv.HikvisionError as exc:
        logger = logging.getLogger(__name__)
        logger.warning("Snapshot xatosi: %r", exc)
        data = None

    if not data:
        # SIMULATION / xato — virtual kadr
        from . import simulation

        seed = camera.id * 7919 + int(time.time() // 30)
        img = simulation.demo_frame(seed)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
        content_type = "image/png"
    else:
        content_type = "image/jpeg"

    resp = HttpResponse(data, content_type=content_type)
    resp["Cache-Control"] = "no-store, max-age=0"
    return resp


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
# BOOTH CSV EXPORT — stend egasi o'z mehmonlarini yuklab oladi
# ==========================================================

@login_required
def booth_visitors_export_csv(request, booth_id):
    booth = get_object_or_404(Booth, pk=booth_id)

    # Faqat shu stend egasi yoki admin
    if not is_admin(request.user) and booth.owner_id != request.user.id:
        messages.error(request, "Ushbu stendga kirish huquqi yo'q.")
        return redirect("expo_analytics")

    visitors = ExpoVisitor.objects.filter(
        tracking_events__booth=booth,
    ).distinct()

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"stend_{booth.booth_number}_visitors.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")

    writer = csv.writer(response)
    writer.writerow([
        "Ism", "Familiya", "Kompaniya", "Maqsad", "Telefon",
        "Kirish vaqti", "Chiqish vaqti", "Ichkaridagi daqiqalar",
    ])
    for v in visitors:
        writer.writerow([
            v.first_name,
            v.last_name,
            v.company,
            v.get_purpose_display(),
            v.phone,
            timezone_fmt(v.check_in_at),
            timezone_fmt(v.check_out_at) if v.check_out_at else "",
            v.minutes_inside,
        ])

    return response


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
        "ID", "Ism", "Familiya", "Kompaniya", "Turi", "Maqsad",
        "Kirish usuli", "Telefon", "Email", "Holat",
        "Kirish vaqti", "Chiqish vaqti",
        "Ichkaridagi daqiqalar", "Oxirgi zona",
    ])

    source_label = {
        "KIOSK": "Kiosk",
        "GATE_QR": "Darvoza — QR",
        "GATE_WALKIN": "Darvoza — joyida",
        "OFFLINE": "Offline navbat",
    }
    type_label = {
        "VISITOR": "Mehmon",
        "EXHIBITOR": "Eksponent",
    }

    for v in ExpoVisitor.objects.order_by("-check_in_at"):
        writer.writerow([
            v.id,
            v.first_name,
            v.last_name,
            v.company,
            type_label.get(v.visit_type, v.visit_type),
            v.get_purpose_display(),
            source_label.get(v.source, v.source),
            v.phone,
            v.email,
            "Ichkarida" if v.is_active else "Chiqib ketdi",
            timezone_fmt(v.check_in_at),
            timezone_fmt(v.check_out_at) if v.check_out_at else "",
            v.minutes_inside,
            v.current_zone,
        ])

    return response


# ==========================================================
# PDF EXPORT — hisobotlarni PDF sifatida yuklab olish
# ==========================================================

@login_required
def booth_report_pdf(request):
    """Stend analitikasi PDF hisoboti."""
    if not is_admin(request.user):
        messages.error(request, "Ushbu sahifaga kirish huquqi yo'q.")
        return redirect("dashboard_home")

    from .pdf import build_booth_report_pdf
    pdf_bytes = build_booth_report_pdf()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="expo_booth_analysis.pdf"'
    return response


@login_required
def visitors_report_pdf(request):
    """Mehmonlar ro'yxati PDF hisoboti."""
    if not can_monitor(request.user):
        messages.error(request, "Ushbu sahifaga kirish huquqi yo'q.")
        return redirect("dashboard_home")

    from .pdf import build_visitors_report_pdf
    pdf_bytes = build_visitors_report_pdf()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="expo_visitors.pdf"'
    return response



# ==========================================================
# DARVOZA (GATE) — manager telefoni uchun offline-friendly skaner
# ==========================================================

def gate_scan(request):
    """Manager skaner sahifasi (QR + joyida ro'yxat + offline navbat)."""
    if not can_monitor(request.user):
        messages.error(request, "Ushbu sahifaga kirish huquqi yo'q.")
        return redirect("dashboard_home")
    return render(request, "expo/gate.html", {})


def gate_scan_api(request):
    """
    Skanerlangan QR yoki walk-in ma'lumot asosida mehmonni kiritish.

    POST JSON:
        qr_text / first_name / last_name / company / phone / purpose /
        visit_type / offline_id / photo_data

    Javob:
        {"success": bool, "status": "ok"|"already"|"error",
         "visitor_id": ..., "full_name": ..., "message": ...}
    """
    if not can_monitor(request.user):
        return JsonResponse({"success": False, "status": "error",
                             "message": "Kirish huquqi yo'q"}, status=403)

    if request.method != "POST":
        return JsonResponse({"success": False, "status": "error",
                             "message": "Faqat POST so'rov qabul qilinadi"}, status=405)

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = request.POST.dict()

    if isinstance(payload, list):
        # Bir nechta yozuv — batch sinxronlash
        results = gate.sync_offline_batch(payload)
        return JsonResponse({"success": True, "results": results})

    payload["created_by"] = request.user

    try:
        visitor, created, status, message = gate.create_visitor_from_scan(payload)
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "status": "error",
                             "message": f"Xato: {exc}"}, status=500)

    if status == "error":
        return JsonResponse({"success": False, "status": "error",
                             "message": message}, status=400)

    return JsonResponse({
        "success": status != "error",
        "status": status,
        "created": created,
        "visitor_id": getattr(visitor, "pk", None),
        "full_name": getattr(visitor, "full_name", ""),
        "badge_token": getattr(visitor, "badge_token", None) and str(visitor.badge_token),
        "message": message,
    })


def gate_auto_qr(request, registration_id):
    """
    Bot ro'yxatdan o'tgan mijoz uchun darvoza QR kartasi (data URL PNG).

    QR ichiga Ticket ID (UUID) qo'yiladi — manager skaneri shu orqali
    mijozni topib, ichkariga kiritadi va kuzatuvni boshlaydi.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "Login talab qilinadi"}, status=401)

    from registrations.models import Registration

    registration = get_object_or_404(
        Registration.objects.select_related("event"),
        pk=registration_id,
    )
    if registration.attendee_id != request.user.id:
        return JsonResponse({"success": False, "message": "Kirish huquqi yo'q"}, status=403)

    import io as _io

    payload = (
        f"Ticket ID:\n{registration.ticket_code}\n\n"
        f"Attendee:\n{registration.attendee.username}\n\n"
        f"Event:\n{registration.event.title}\n"
    )
    qr = qrcode.make(payload, box_size=8, border=2)
    buf = _io.BytesIO()
    qr.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return JsonResponse({
        "success": True,
        "data_uri": f"data:image/png;base64,{b64}",
        "ticket_code": str(registration.ticket_code),
    })
