import stripe

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import ProcessedWebhook, Payment
from movies.models import Booking, Seat
from movies.email_worker import queue_booking_email
from django.db import transaction


@csrf_exempt
def stripe_webhook(request):

    payload = request.body

    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )

    except ValueError:
        return HttpResponse("Invalid payload", status=400)

    except stripe.error.SignatureVerificationError:
        return HttpResponse("Invalid signature", status=400)

    # ----------------------------
    # Idempotency check
    # ----------------------------
    event_id = event["id"]

    if ProcessedWebhook.objects.filter(stripe_event_id=event_id).exists():
        return HttpResponse("Already processed", status=200)

    ProcessedWebhook.objects.create(stripe_event_id=event_id)

    event_type = event["type"]

    print(f"Stripe webhook received: {event_type}")

    # ----------------------------
    # EVENT HANDLING
    # ----------------------------
   # ----------------------------
    # EVENT HANDLING
    # ----------------------------
    if event_type == "checkout.session.completed":

        session = event["data"]["object"]

        try:

            payment = Payment.objects.get(
                stripe_session_id=session["id"]
            )

            # Extra protection against duplicate processing
            if payment.status == "paid":
                return HttpResponse(status=200)

            payment.status = "paid"

            if "payment_intent" in session:
                payment.stripe_payment_intent_id = session["payment_intent"]

            payment.save()

            booking_ids = []

            with transaction.atomic():

                for seat_id in payment.selected_seats:

                    seat = Seat.objects.select_for_update().get(
                        id=seat_id
                    )

                    if seat.is_booked:
                        continue

                    seat.is_booked = True
                    seat.save()

                    booking = Booking.objects.create(
                        user=payment.user,
                        seat=seat,
                        movie=payment.theater.movie,
                        theater=payment.theater
                    )

                    booking_ids.append(booking.id)

            if booking_ids:

                queue_booking_email(
                    booking_ids,
                    payment.user.email
                )

            print(
                f"Payment {payment.id} confirmed "
                f"with {len(booking_ids)} bookings"
            )

        except Payment.DoesNotExist:

            print(
                f"Payment not found for session "
                f"{session['id']}"
            )

    elif event_type == "payment_intent.succeeded":
        # optional logging only
        print("Payment intent succeeded")

    elif event_type == "charge.updated":
        # ignore
        pass

    elif event_type == "payment_intent.created":
        # ignore
        pass

    elif event_type == "payment_intent.payment_failed":

        intent = event["data"]["object"]

        Payment.objects.filter(
            stripe_payment_intent_id=intent["id"]
        ).update(status="failed")

    elif event_type == "payment_intent.canceled":

        intent = event["data"]["object"]

        Payment.objects.filter(
            stripe_payment_intent_id=intent["id"]
        ).update(status="cancelled")

    return HttpResponse(status=200)