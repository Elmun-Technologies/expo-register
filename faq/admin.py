from django.contrib import admin

from .models import FAQ


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):

    list_display = (
        "question",
        "event",
        "display_order",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "event",
    )

    search_fields = (
        "question",
        "answer",
        "event__title",
    )

    ordering = (
        "event",
        "display_order",
    )