from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
import stripe

import uuid

from django.contrib.auth.decorators import login_required

from .models import Payment
from movies.models import Theater

stripe.api_key = settings.STRIPE_SECRET_KEY


def payment_success(request):

    payment_id = request.GET.get("payment_id")

    payment = None

    if payment_id:
        payment = Payment.objects.filter(
            id=payment_id
        ).first()

    return render(
        request,
        "payments/payment_success.html",
        {
            "payment": payment
        }
    )


def payment_cancel(request):
    return render(
        request,
        "payments/payment_cancel.html"
    )


@login_required
def create_checkout_session(request):

    theater_id = request.GET.get("theater_id")
    seat_ids = request.GET.get("seat_ids")

    if not theater_id or not seat_ids:
        return HttpResponse(
            "Missing booking information",
            status=400
        )

    theater = Theater.objects.get(
        id=theater_id
    )

    selected_seat_list = seat_ids.split(",")

    idempotency_key = uuid.uuid4().hex

    payment = Payment.objects.create(
        user=request.user,
        theater=theater,
        selected_seats=selected_seat_list,
        amount=150.00,
        status="pending",
        idempotency_key=idempotency_key,
    )

    try:

        checkout_session = stripe.checkout.Session.create(

            payment_method_types=["card"],

            mode="payment",

            line_items=[
                {
                    "price_data": {
                        "currency": "inr",
                        "product_data": {
                            "name": "BookMySeat Ticket",
                        },
                        "unit_amount": 15000,
                    },
                    "quantity": 1,
                }
            ],

            metadata={
                "payment_id": str(payment.id),
            },

            success_url=request.build_absolute_uri(
                f"/payments/success/?payment_id={payment.id}"
            ),

            cancel_url=request.build_absolute_uri(
                "/payments/cancel/"
            ),
        )

        payment.stripe_session_id = checkout_session.id
        payment.save()

        return redirect(
            checkout_session.url
        )

    except Exception as e:

        payment.status = "failed"
        payment.save()

        return HttpResponse(
            f"Stripe Error: {str(e)}",
            status=500
        )