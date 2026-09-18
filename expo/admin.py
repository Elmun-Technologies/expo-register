from django.contrib import admin

from .models import Booth, Camera, ExpoVisitor, TrackingEvent, VisitAlert


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
    list_display = ("full_name", "company", "purpose", "status", "check_in_at")
    list_filter = ("status", "purpose")
    search_fields = ("first_name", "last_name", "company")


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display = ("visitor", "kind", "zone", "camera", "booth", "detected_at")
    list_filter = ("kind",)


@admin.register(VisitAlert)
class VisitAlertAdmin(admin.ModelAdmin):
    list_display = ("visitor", "level", "message", "created_at")
    list_filter = ("level",)
