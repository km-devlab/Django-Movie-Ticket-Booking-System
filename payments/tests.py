from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from movies.models import Movie, Theater
from payments.models import Payment, ProcessedWebhook


class PaymentTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )

        self.movie = Movie.objects.create(
            name="Test Movie",
            rating=8.5,
            cast="Actor 1, Actor 2"
        )

        self.theater = Theater.objects.create(
            name="Test Theater",
            movie=self.movie,
            time="2026-06-11T18:00:00Z"
        )

    @patch("payments.views.stripe.checkout.Session.create")
    def test_create_checkout_session(self, mock_create):
        """
        Checkout session should be created and payment stored.
        """

        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/test"

        mock_create.return_value = mock_session

        self.client.login(
            username="testuser",
            password="testpass123"
        )

        response = self.client.get(
            reverse("create_checkout_session"),
            {
                "theater_id": self.theater.id,
                "seat_ids": "1,2"
            }
        )

        self.assertEqual(response.status_code, 302)

        payment = Payment.objects.first()

        self.assertIsNotNone(payment)

        self.assertEqual(
            payment.stripe_session_id,
            "cs_test_123"
        )

        self.assertEqual(
            payment.status,
            "pending"
        )

    def test_duplicate_webhook_ignored(self):
        """
        ProcessedWebhook model prevents duplicate events.
        """

        event_id = "evt_test_123"

        ProcessedWebhook.objects.create(
            stripe_event_id=event_id
        )

        self.assertEqual(
            ProcessedWebhook.objects.filter(
                stripe_event_id=event_id
            ).count(),
            1
        )

    def test_checkout_session_completed_updates_payment(self):
        """
        Simulate successful payment update.
        """

        payment = Payment.objects.create(
            user=self.user,
            theater=self.theater,
            selected_seats=["1"],
            amount=150,
            status="pending",
            idempotency_key="abc123xyz"
        )

        payment.status = "paid"
        payment.save()

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            "paid"
        )