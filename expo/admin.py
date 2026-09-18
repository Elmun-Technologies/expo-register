from django.contrib import admin

from .models import Booth, Camera, ExpoVisitor, TelegramProfile, TrackingEvent, VisitAlert


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "kind", "user", "state", "created_at")
    list_filter = ("kind", "state")
    search_fields = ("username", "first_name", "last_name", "telegram_id")


@admin.register(Booth)
class BoothAdmin(admin.ModelAdmin):
    list_display = ("booth_number", "name", "zone", "owner")
    search_fields = ("name", "booth_number", "zone")


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "mode", "is_enabled", "is_online", "ip_address")
    list_filter = ("mode", "is_enabled", "is_online")
    search_fields = ("name", "zone", "ip_address")


@admin.register(ExpoVisitor)
class ExpoVisitorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "company", "visit_type", "purpose", "source", "status", "check_in_at")
    list_filter = ("status", "purpose", "visit_type", "source")
    search_fields = ("first_name", "last_name", "company")


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display = ("visitor", "kind", "zone", "camera", "booth", "detected_at")
    list_filter = ("kind",)


@admin.register(VisitAlert)
class VisitAlertAdmin(admin.ModelAdmin):
    list_display = ("visitor", "level", "message", "created_at")
    list_filter = ("level",)
