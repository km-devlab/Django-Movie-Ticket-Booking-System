# Payment Gateway Integration with Idempotency and Webhook Security

## Overview

This project integrates Stripe Checkout into the Movie Ticket Booking System to securely process ticket purchases.

The implementation focuses on:

* Secure server-side payment verification
* Stripe webhook signature validation
* Idempotency protection against duplicate webhook delivery
* Prevention of duplicate bookings
* Payment success, failure, and cancellation handling
* Replay attack mitigation
* Graceful handling of payment interruptions and retries

---

# Payment Lifecycle

## Step 1: Seat Selection

The user selects one or more available seats for a movie show.

Selected seat IDs and theater information are passed to the payment module.

---

## Step 2: Checkout Session Creation

The backend creates a Stripe Checkout Session.

During this step:

* A unique idempotency key is generated.
* A Payment record is created with status `pending`.
* Selected seats are temporarily associated with the Payment record.
* Stripe Checkout Session is created using the Stripe SDK.

Example Payment state:

```
status = pending
stripe_session_id = generated_by_stripe
idempotency_key = unique_uuid
```

The user is redirected to Stripe's hosted payment page.

---

## Step 3: Payment Processing by Stripe

Stripe securely collects payment information.

Possible outcomes:

### Success

Customer completes payment successfully.

### Failure

Payment is declined or cannot be processed.

### Cancellation

Customer abandons or cancels payment before completion.

---

## Step 4: Webhook Delivery

Stripe sends webhook events to:

```
/payments/webhook/
```

Examples:

```
checkout.session.completed
payment_intent.payment_failed
payment_intent.canceled
```

The application never trusts frontend redirects alone.

All payment state changes are performed using verified webhook events.

---

## Step 5: Webhook Signature Verification

Every incoming webhook is validated using Stripe's signing secret.

```
stripe.Webhook.construct_event(...)
```

Invalid payloads return:

```
HTTP 400
```

Invalid signatures return:

```
HTTP 400
```

This prevents forged requests from impersonating Stripe.

---

## Step 6: Idempotency Protection

Stripe may retry webhook events if:

* Network failures occur
* Server responses timeout
* Delivery confirmation is not received

To prevent duplicate processing:

A ProcessedWebhook table stores every Stripe event ID.

Before processing:

```
if ProcessedWebhook.objects.filter(
    stripe_event_id=event_id
).exists():
    return HttpResponse("Already processed")
```

Benefits:

* Prevents duplicate booking creation
* Prevents duplicate payment updates
* Protects against replay attacks
* Makes webhook handling safe during retries

---

## Step 7: Successful Payment Handling

When:

```
checkout.session.completed
```

is received:

The system:

1. Locates the matching Payment record.
2. Updates status to:

```
paid
```

3. Stores Stripe payment information.
4. Creates final booking records.
5. Marks seats as booked.
6. Sends booking confirmation email.

Result:

```
Payment -> paid
Booking -> created
Seats -> locked
Email -> sent
```

---

## Step 8: Payment Failure Handling

When:

```
payment_intent.payment_failed
```

is received:

The Payment record is updated to:

```
failed
```

No booking is created.

Seats remain available.

---

## Step 9: Payment Cancellation Handling

When:

```
payment_intent.canceled
```

is received:

The Payment record is updated to:

```
cancelled
```

No booking is created.

Seats remain available.

---

# Fraud Prevention Measures

## Server-Side Verification

Payment success is determined only through Stripe webhooks.

Frontend redirects alone are never trusted.

---

## Signature Validation

All webhook payloads are validated using Stripe's webhook secret.

This prevents unauthorized requests.

---

## Idempotency Keys

Every checkout session uses a unique idempotency key.

Benefits:

* Prevents duplicate payment creation
* Protects against accidental retries
* Ensures safe request reprocessing

---

## Replay Attack Protection

Stripe event IDs are stored in the ProcessedWebhook table.

Previously processed events are ignored.

This prevents:

* Duplicate bookings
* Duplicate payment updates
* Replay attacks

---

# Timeout and Partial Failure Handling

Stripe automatically retries webhook delivery when:

* The server is unavailable
* Network interruptions occur
* A timeout is encountered

Because webhook processing is idempotent, retries are safe.

Duplicate events do not create duplicate bookings.

---

# Local Testing

## Start Django

```
python manage.py runserver
```

## Start Stripe Listener

```
stripe listen --forward-to localhost:8000/payments/webhook/
```

## Complete Test Payment

```
http://127.0.0.1:8000/payments/checkout/?theater_id=<id>
```

## Trigger Test Events

```
stripe trigger checkout.session.completed
```

```
stripe trigger payment_intent.payment_failed
```

```
stripe trigger payment_intent.canceled
```

## Verify Results

Check:

* Payment status updates
* ProcessedWebhook entries
* Booking creation
* Seat locking
* Email delivery
* Duplicate webhook handling

---

# Conclusion

The implementation provides secure Stripe payment processing with webhook signature verification, idempotent event handling, replay attack protection, payment lifecycle tracking, and support for successful, failed, cancelled, and retried transactions.
