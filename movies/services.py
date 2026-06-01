import logging
import ssl
from smtplib import SMTP
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger('movies.email')

# --- MONKEY PATCH FOR DJANGO 3.2 + PYTHON 3.12+ COMPATIBILITY ---
# This forcibly stops Python from throwing the 'keyfile' crash error
old_starttls = SMTP.starttls
def new_starttls(self, keyfile=None, certfile=None, context=None):
    if context is None:
        context = ssl.create_default_context()
    # Remove keyfile and certfile parameters as they are deprecated/broken in newer Python versions
    return old_starttls(self, context=context)
SMTP.starttls = new_starttls
# -----------------------------------------------------------------

def send_booking_confirmation_email(recipient_email, booking_context):
    """
    Renders the email template and sends the confirmation email.
    """
    try:
        # 1. Render HTML Content from Template
        html_content = render_to_string('emails/booking_confirmation.html', booking_context)
        text_content = strip_tags(html_content)

        subject = "Your Ticket Confirmation - BookMySeat"
        from_email = settings.DEFAULT_FROM_EMAIL
        to = [recipient_email]

        # 2. Assemble and Send Email
        email = EmailMultiAlternatives(subject, text_content, from_email, to)
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        print("🚀 [SUCCESS] Booking email sent out successfully!")
        return True

    except Exception as e:
        logger.error(f"Failed to send booking confirmation email to {recipient_email}. Error: {str(e)}")
        print(f"❌ [ERROR] Email delivery failed: {e}")
        return False