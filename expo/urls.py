from django.urls import path

from . import views

urlpatterns = [
    # Kiosk — mehmon kirishi (ochiq)
    path("kiosk/", views.kiosk, name="expo_kiosk"),

    # Monitoring paneli (xavfsizlik xodimi / admin)
    path("monitor/", views.monitor, name="expo_monitor"),
    path("monitor/live/", views.monitor_live_api, name="expo_monitor_live"),

    # Visitors
    path("visitors/", views.visitors_list, name="expo_visitors"),
    path("visitors/export/", views.visitors_export_csv, name="expo_visitors_export"),
    path("visitors/<int:visitor_id>/", views.visitor_detail, name="expo_visitor_detail"),
    path("visitors/<int:visitor_id>/badge/", views.visitor_badge, name="expo_visitor_badge"),

    # Devices (kameralar va stendlar)
    path("devices/", views.devices, name="expo_devices"),
    path("devices/camera/<int:camera_id>/toggle/", views.camera_toggle, name="expo_camera_toggle"),

    # Stend analitikasi
    path("analytics/", views.booth_analytics, name="expo_analytics"),
    path("analytics/booth/<int:booth_id>/", views.api_booth_stats, name="expo_booth_stats"),

    # API (simulyatsiya / kuzatuv)
    path("api/advance/<int:visitor_id>/", views.api_advance, name="expo_api_advance"),
    path("api/path/<int:visitor_id>/", views.api_visitor_path, name="expo_api_path"),
]
