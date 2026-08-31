from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):

    list_display = (
        "event",
        "attendee",
        "organizer",
        "updated_at",
        "created_at",
    )

    list_filter = (
        "event",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "event__title",
        "attendee__username",
        "organizer__username",
    )

    ordering = (
        "-updated_at",
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):

    list_display = (
        "sender",
        "conversation",
        "is_read",
        "created_at",
    )

    list_filter = (
        "is_read",
        "created_at",
    )

    search_fields = (
        "content",
        "sender__username",
        "conversation__event__title",
    )

    ordering = (
        "-created_at",
    )