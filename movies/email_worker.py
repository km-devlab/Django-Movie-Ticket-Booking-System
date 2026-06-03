import os
import sys
import time
import uuid
import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Booking, EmailTask

# Configure logger
logger = logging.getLogger('movies.email')
_worker_started = False

def mask_email(email):
    """
    Mask recipient email addresses to prevent exposure of sensitive data in logs.
    e.g. gabriel@gmail.com -> g***************@gmail.com
    """
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        return f"{local}*@{domain}"
    return f"{local[0]}{'*' * 15}@{domain}"


def queue_booking_email(booking_ids, recipient_email):
    """
    Retrieves booking details, renders HTML/text templates,
    and inserts an EmailTask in the queue.
    """
    if not recipient_email:
        logger.error("Failed to queue booking confirmation email: recipient email is empty")
        return
        
    try:
        bookings = Booking.objects.filter(id__in=booking_ids).select_related('movie', 'theater', 'seat', 'user').order_by('seat__seat_number')
        if not bookings.exists():
            logger.error("Failed to queue booking confirmation email: no bookings found")
            return
            
        first_booking = bookings.first()
        user = first_booking.user
        movie = first_booking.movie
        theater = first_booking.theater
        
        seat_numbers = ", ".join([b.seat.seat_number for b in bookings])
        payment_id = f"BMS-{uuid.uuid4().hex[:12].upper()}"
        
        # Calculate pricing (mock ₹150 per ticket)
        ticket_price = 150
        total_price = len(bookings) * ticket_price
        
        # Prepare template context
        context = {
            'user': user,
            'movie': movie,
            'theater': theater,
            'seat_numbers': seat_numbers,
            'payment_id': payment_id,
            'ticket_count': len(bookings),
            'total_price': f"₹{total_price}",
            'show_time': theater.time.strftime("%d %b %Y, %I:%M %p"),
            'booking_date': timezone.now().strftime("%d %b %Y, %I:%M %p"),
        }
        
        # Render contents using Django template engine
        html_content = render_to_string('emails/booking_confirmation.html', context)
        text_content = render_to_string('emails/booking_confirmation.txt', context)
        
        subject = f"Booking Confirmed: {movie.name}"
        
        # Create EmailTask record
        EmailTask.objects.create(
            recipient=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            payment_id=payment_id,
            status='pending',
            retry_at=timezone.now()
        )
        
    except Exception as e:
        logger.exception("Error while queuing booking confirmation email")


def process_pending_email_tasks():
    """
    Queries and processes any pending email tasks.
    Uses atomic locks to ensure multiple worker threads do not process the same task.
    """
    now = timezone.now()
    # Find email tasks that are pending and ready for processing/retry
    pending_tasks = EmailTask.objects.filter(status='pending', retry_at__lte=now).order_by('created_at')
    
    for task in pending_tasks:
        # Atomic lock
        with transaction.atomic():
            locked_rows = EmailTask.objects.filter(id=task.id, status='pending').update(status='processing')
            if locked_rows == 0:
                # Task already picked up by another worker/thread
                continue
        
        # Try to send the email
        try:
            msg = EmailMultiAlternatives(
                subject=task.subject,
                body=task.text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'BookMySeat <noreply@bookmyseat.com>'),
                to=[task.recipient]
            )
            msg.attach_alternative(task.html_content, "text/html")
            msg.send()
            
            # Successfully sent
            task.status = 'sent'
            task.save()
            logger.info("Booking confirmation email sent payment_id=%s recipient=%s", task.payment_id, mask_email(task.recipient))
            
        except Exception as e:
            error_msg = str(e)
            # Log failure with current retry count
            logger.error(
                "Booking confirmation email failed payment_id=%s recipient=%s retry=%s error=%r",
                task.payment_id,
                mask_email(task.recipient),
                task.retry_count,
                error_msg,
            )
            
            task.retry_count += 1
            if task.retry_count >= task.max_retries:
                task.status = 'failed'
                task.error_message = error_msg
                task.save()
            else:
                task.status = 'pending'
                task.error_message = error_msg
                task.retry_at = timezone.now() + timedelta(seconds=5 * (2 ** (task.retry_count - 1)))
                task.save()


def email_worker_loop():
    """
    Infinite loop for the background worker thread.
    Polls the database for pending email tasks every 5 seconds.
    """
    logger.info("Background email worker thread started.")
    while True:
        try:
            process_pending_email_tasks()
        except (OperationalError, ProgrammingError):
            # Safe handling if tables have not been fully migrated or db is locked temporarily
            pass
        except Exception as e:
            logger.exception(f"Unexpected error in background email worker loop: {str(e)}")
            
        # Poll every 5 seconds
        time.sleep(5)


def start_email_worker():
    """
    Starts the background worker thread as a daemon thread.
    """
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    worker_thread = threading.Thread(target=email_worker_loop, name="EmailWorkerThread", daemon=True)
    worker_thread.start()
