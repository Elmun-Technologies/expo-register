from django.contrib import admin

from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):

    list_display = (
        "event",
        "attendee",
        "rating",
        "created_at",
    )

    list_filter = (
        "rating",
        "created_at",
    )

    search_fields = (
        "event__title",
        "attendee__username",
        "comment",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )