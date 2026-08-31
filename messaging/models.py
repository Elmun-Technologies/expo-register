from django.conf import settings
from django.db import models

from events.models import Event


class Conversation(models.Model):
    """
    A private conversation between an event attendee
    and the organizer of that event.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="conversations",
    )

    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_conversations_as_attendee",
    )

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_conversations_as_organizer",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-updated_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "event",
                    "attendee",
                    "organizer",
                ],
                name="unique_event_conversation",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "attendee",
                    "updated_at",
                ]
            ),
            models.Index(
                fields=[
                    "organizer",
                    "updated_at",
                ]
            ),
            models.Index(
                fields=[
                    "event",
                    "updated_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.event.title} - "
            f"{self.attendee.username} ↔ "
            f"{self.organizer.username}"
        )


class Message(models.Model):
    """
    Individual message inside an event conversation.
    """

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_event_messages",
    )

    content = models.TextField(
        max_length=5000,
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "conversation",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "conversation",
                    "is_read",
                ]
            ),
            models.Index(
                fields=[
                    "sender",
                    "created_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.sender.username}: "
            f"{self.content[:50]}"
        )