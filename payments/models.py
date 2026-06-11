from django.db import models
from django.contrib.auth.models import User
from movies.models import Theater


class Payment(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    theater = models.ForeignKey(
        Theater,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    selected_seats = models.JSONField()

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    stripe_session_id = models.CharField(
        max_length=255,
        blank=True
    )

    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True
    )

    idempotency_key = models.CharField(
        max_length=64,
        unique=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Payment #{self.id} ({self.status})"


class ProcessedWebhook(models.Model):

    stripe_event_id = models.CharField(
        max_length=255,
        unique=True
    )

    processed_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.stripe_event_id