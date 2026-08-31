from django.conf import settings
from django.db import models

from events.models import Event


class Feedback(models.Model):

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="feedback",
    )

    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_feedback",
    )

    rating = models.PositiveSmallIntegerField(
    choices=[
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    ],
)

    comment = models.TextField(
        blank=True,
        max_length=2000,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "event",
                    "attendee",
                ],
                name="unique_event_feedback",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "event",
                    "created_at",
                ],
            ),
            models.Index(
                fields=[
                    "attendee",
                    "created_at",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.attendee.username} - "
            f"{self.event.title} - "
            f"{self.rating}/5"
        )