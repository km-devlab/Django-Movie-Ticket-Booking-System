from django.core.management.base import BaseCommand
from movies.models import Seat, Booking, EmailTask

class Command(BaseCommand):
    help = 'Reset seat availability, delete all bookings, and clear email queue (local DB)'

    def handle(self, *args, **options):
        # Delete all bookings
        Booking.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Deleted all Booking records'))

        # Reset seat availability
        updated = Seat.objects.update(is_booked=False)
        self.stdout.write(self.style.SUCCESS(f'Reset is_booked for {updated} Seat records'))

        # Clear email task queue (including pending, processing, etc.)
        EmailTask.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Cleared all EmailTask records'))
