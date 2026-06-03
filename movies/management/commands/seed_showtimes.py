from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from movies.models import Booking, EmailTask, Movie, Seat, Theater


CINEMA_NAMES = [
    "PVR Nexus Mall",
    "INOX City Centre",
    "Cinepolis Prime",
    "Miraj Cinemas",
    "Carnival Grand",
]


class Command(BaseCommand):
    help = "Create realistic theater showtimes and seat maps for testing."

    def add_arguments(self, parser):
        parser.add_argument("--movies", type=int, default=24, help="Number of movies to seed with showtimes.")
        parser.add_argument("--theaters-per-movie", type=int, default=4, help="Theaters/showtimes per movie.")
        parser.add_argument("--rows", type=int, default=8, help="Seat rows per theater.")
        parser.add_argument("--cols", type=int, default=10, help="Seats per row.")
        parser.add_argument(
            "--clear-bookings",
            action="store_true",
            help="Delete bookings/email tasks and unlock existing seats before seeding.",
        )
        parser.add_argument(
            "--replace-showtimes",
            action="store_true",
            help="Delete existing theaters/seats and create a fresh showtime layout.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear_bookings"]:
            Booking.objects.all().delete()
            EmailTask.objects.all().delete()
            Seat.objects.update(is_booked=False)
        if options["replace_showtimes"]:
            Theater.objects.all().delete()

        movies = list(Movie.objects.order_by("id")[: options["movies"]])
        if not movies:
            self.stderr.write(self.style.ERROR("No movies found. Run seed_movie_catalog first."))
            return

        base_time = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        rows = options["rows"]
        cols = options["cols"]
        theaters_per_movie = options["theaters_per_movie"]

        created_theaters = 0
        created_seats = 0

        for movie_index, movie in enumerate(movies):
            for show_index in range(theaters_per_movie):
                cinema_name = CINEMA_NAMES[(movie_index + show_index) % len(CINEMA_NAMES)]
                show_time = base_time + timedelta(
                    days=movie_index % 7,
                    hours=(show_index * 3) + (movie_index % 3),
                )

                theater, theater_created = Theater.objects.get_or_create(
                    movie=movie,
                    name=cinema_name,
                    time=show_time,
                )
                if theater_created:
                    created_theaters += 1

                existing_seats = set(
                    Seat.objects.filter(theater=theater).values_list("seat_number", flat=True)
                )
                new_seats = []
                for row_index in range(rows):
                    row_label = chr(ord("A") + row_index)
                    for col in range(1, cols + 1):
                        seat_number = f"{row_label}{col}"
                        if seat_number not in existing_seats:
                            new_seats.append(Seat(theater=theater, seat_number=seat_number))

                Seat.objects.bulk_create(new_seats, batch_size=500)
                created_seats += len(new_seats)

        self.stdout.write(
            self.style.SUCCESS(
                f"Showtime seed complete: {len(movies)} movies, "
                f"{created_theaters} new theaters/showtimes, {created_seats} new seats."
            )
        )
