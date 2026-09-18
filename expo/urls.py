from django.http import HttpResponse
from django.urls import path

from . import views


def gate_service_worker(request):
    """Offline gate uchun Service Worker JS (to'g'ri MIME bilan)."""
    body = ""
    from pathlib import Path
    sw = Path(__file__).parent / "static" / "expo" / "js" / "gate-sw.js"
    if sw.exists():
        body = sw.read_text(encoding="utf-8")
    return HttpResponse(
        body,
        content_type="application/javascript; charset=utf-8",
    )

urlpatterns = [
    # Kiosk — mehmon kirishi (ochiq)
    path("kiosk/", views.kiosk, name="expo_kiosk"),

    # Monitoring paneli (xavfsizlik xodimi / admin)
    path("monitor/", views.monitor, name="expo_monitor"),
    path("monitor/live/", views.monitor_live_api, name="expo_monitor_live"),

    # Visitors
    path("visitors/", views.visitors_list, name="expo_visitors"),
    path("visitors/export/", views.visitors_export_csv, name="expo_visitors_export"),
    path("visitors/pdf/", views.visitors_report_pdf, name="expo_visitors_pdf"),
    path("visitors/<int:visitor_id>/", views.visitor_detail, name="expo_visitor_detail"),
    path("visitors/<int:visitor_id>/badge/", views.visitor_badge, name="expo_visitor_badge"),

    # Devices (kameralar va stendlar)
    path("devices/", views.devices, name="expo_devices"),
    path("devices/camera/<int:camera_id>/toggle/", views.camera_toggle, name="expo_camera_toggle"),

    # Stend analitikasi
    path("analytics/", views.booth_analytics, name="expo_analytics"),
    path("analytics/pdf/", views.booth_report_pdf, name="expo_analytics_pdf"),
    path("analytics/booth/<int:booth_id>/", views.api_booth_stats, name="expo_booth_stats"),
    path("analytics/booth/<int:booth_id>/export/", views.booth_visitors_export_csv, name="expo_booth_export"),

    # API (simulyatsiya / kuzatuv)
    path("api/advance/<int:visitor_id>/", views.api_advance, name="expo_api_advance"),
    path("api/path/<int:visitor_id>/", views.api_visitor_path, name="expo_api_path"),

    # Darvoza (gate) — manager telefoni: QR skaner + offline navbat
    path("gate/", views.gate_scan, name="expo_gate"),
    path("gate/api/", views.gate_scan_api, name="expo_gate_api"),
    path("gate/auto-qr/<int:registration_id>/", views.gate_auto_qr, name="expo_gate_auto_qr"),
    path("gate/sw.js", gate_service_worker, name="expo_gate_sw"),
]
