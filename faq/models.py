from django.db import models

from events.models import Event


class FAQ(models.Model):
    """
    Frequently Asked Question for an Event.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="faqs",
    )

    question = models.CharField(
        max_length=300,
    )

    answer = models.TextField()

    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers are displayed first.",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "event",
                    "is_active",
                ]
            ),
            models.Index(
                fields=[
                    "event",
                    "display_order",
                ]
            ),
        ]

        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return f"{self.event.title} - {self.question}"