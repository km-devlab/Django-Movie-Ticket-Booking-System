from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Genre, Language, Movie


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class MovieFilteringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.action = Genre.objects.create(name="Action", slug="action")
        cls.drama = Genre.objects.create(name="Drama", slug="drama")
        cls.comedy = Genre.objects.create(name="Comedy", slug="comedy")
        cls.english = Language.objects.create(name="English", slug="english")
        cls.hindi = Language.objects.create(name="Hindi", slug="hindi")

        cls._movie("Alpha", "Action cast", 8.1, [cls.action], [cls.english])
        cls._movie("Beta", "Drama cast", 7.5, [cls.drama], [cls.hindi])
        cls._movie("Gamma", "Comedy cast", 6.5, [cls.comedy], [cls.english])
        cls._movie("Delta", "Action drama cast", 9.0, [cls.action, cls.drama], [cls.hindi])

    @classmethod
    def _movie(cls, name, cast, rating, genres, languages):
        movie = Movie.objects.create(
            name=name,
            image="movies/test.jpg",
            rating=rating,
            cast=cast,
            description="Test movie",
        )
        movie.genres.set(genres)
        movie.languages.set(languages)
        return movie

    def test_filters_movies_by_multiple_genres_and_language(self):
        response = self.client.get(
            reverse("movie_list"),
            {"genre": ["action", "drama"], "language": "hindi", "sort": "rating"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(
            response.context["movies"],
            ["Delta", "Beta"],
            transform=lambda movie: movie.name,
        )

    def test_genre_counts_apply_language_but_not_selected_genre_filter(self):
        response = self.client.get(
            reverse("movie_list"),
            {"genre": "action", "language": "hindi"},
        )

        counts = {
            genre.slug: genre.movie_count
            for genre in response.context["genres"]
        }
        self.assertEqual(counts["action"], 1)
        self.assertEqual(counts["drama"], 2)
        self.assertEqual(counts["comedy"], 0)

    def test_paginates_filtered_movies(self):
        for index in range(13):
            self._movie(
                f"Extra {index:02d}",
                "Action cast",
                5.0,
                [self.action],
                [self.english],
            )

        response = self.client.get(
            reverse("movie_list"),
            {"genre": "action", "language": "english", "page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_movies"], 14)
        self.assertEqual(len(response.context["movies"]), 2)


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class MovieTrailerTests(TestCase):
    def test_rejects_non_youtube_trailer_url(self):
        movie = Movie(
            name="Unsafe Trailer",
            image="movies/test.jpg",
            rating=7.0,
            cast="Test cast",
            description="Test movie",
            trailer_url="https://evil.example.com/watch?v=zSWdZVtXT7E",
        )

        with self.assertRaises(ValidationError):
            movie.full_clean()

    def test_movie_detail_uses_sanitized_lazy_youtube_embed(self):
        movie = Movie.objects.create(
            name="Safe Trailer",
            image="movies/test.jpg",
            rating=8.0,
            cast="Test cast",
            description="Test movie",
            trailer_url="https://www.youtube.com/watch?v=zSWdZVtXT7E&bad=<script>",
        )

        response = self.client.get(reverse("theater_list", args=[movie.id]))

        self.assertContains(response, "https://www.youtube-nocookie.com/embed/zSWdZVtXT7E")
        self.assertContains(response, 'loading="lazy"')
        self.assertNotContains(response, "bad=")
        self.assertNotContains(response, "&lt;script&gt;")


from unittest.mock import patch
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Seat, Theater, Booking, EmailTask
from .email_worker import queue_booking_email, process_pending_email_tasks, mask_email

class EmailConfirmationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="password")
        cls.movie = Movie.objects.create(
            name="Inception",
            image="movies/test.jpg",
            rating=9.0,
            cast="Leo",
            description="Dream within dream",
        )
        cls.theater = Theater.objects.create(
            name="Cinema Hall 1",
            movie=cls.movie,
            time=timezone.now()
        )
        cls.seat1 = Seat.objects.create(theater=cls.theater, seat_number="A1")
        cls.seat2 = Seat.objects.create(theater=cls.theater, seat_number="A2")

    def test_mask_email_helper(self):
        self.assertEqual(mask_email("gabriel@gmail.com"), "g***************@gmail.com")
        self.assertEqual(mask_email("a@b.com"), "a*@b.com")
        self.assertEqual(mask_email(None), None)
        self.assertEqual(mask_email("notanemail"), "notanemail")

    def test_queue_booking_email_creates_pending_task(self):
        # Create bookings
        booking1 = Booking.objects.create(user=self.user, seat=self.seat1, movie=self.movie, theater=self.theater)
        booking2 = Booking.objects.create(user=self.user, seat=self.seat2, movie=self.movie, theater=self.theater)
        
        # Verify no email tasks exist yet
        self.assertEqual(EmailTask.objects.count(), 0)
        
        # Queue the email
        queue_booking_email([booking1.id, booking2.id], self.user.email)
        
        # Check task created
        self.assertEqual(EmailTask.objects.count(), 1)
        task = EmailTask.objects.first()
        self.assertEqual(task.recipient, self.user.email)
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.retry_count, 0)
        self.assertIn("A1, A2", task.html_content)
        self.assertIn("Cinema Hall 1", task.html_content)
        self.assertIn("₹300", task.html_content) # 2 seats * 150 = 300

    def test_process_pending_email_tasks_success(self):
        booking = Booking.objects.create(user=self.user, seat=self.seat1, movie=self.movie, theater=self.theater)
        queue_booking_email([booking.id], self.user.email)
        
        task = EmailTask.objects.first()
        self.assertEqual(task.status, 'pending')
        
        # Process task (should send email using locmem backend automatically in Django tests)
        process_pending_email_tasks()
        
        # Reload task and check status
        task.refresh_from_db()
        self.assertEqual(task.status, 'sent')
        
        # Verify email was actually "sent" via django.core.mail.outbox
        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(mail.outbox[0].subject, f"Booking Confirmed: {self.movie.name}")
        self.assertIn("A1", mail.outbox[0].body)

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_process_pending_email_tasks_failure_and_retry(self, mock_send):
        # Force sending to fail
        mock_send.side_effect = Exception("SMTP Connection Failed")
        
        booking = Booking.objects.create(user=self.user, seat=self.seat1, movie=self.movie, theater=self.theater)
        queue_booking_email([booking.id], self.user.email)
        
        task = EmailTask.objects.first()
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.retry_count, 0)
        
        # Run process
        process_pending_email_tasks()
        
        # Verify retry state
        task.refresh_from_db()
        self.assertEqual(task.status, 'pending') # Returns to pending for next retry
        self.assertEqual(task.retry_count, 1)
        self.assertEqual(task.error_message, "SMTP Connection Failed")
        self.assertTrue(task.retry_at > timezone.now())

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_process_pending_email_tasks_max_retries_exceeded(self, mock_send):
        mock_send.side_effect = Exception("SMTP Connection Failed")
        
        booking = Booking.objects.create(user=self.user, seat=self.seat1, movie=self.movie, theater=self.theater)
        queue_booking_email([booking.id], self.user.email)
        
        task = EmailTask.objects.first()
        # Simulate that it has already retried twice
        task.retry_count = 2
        task.save()
        
        # Run process (third attempt)
        process_pending_email_tasks()
        
        # Should now be failed
        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')
        self.assertEqual(task.retry_count, 3)

    @patch("movies.views.queue_booking_email")
    def test_booking_view_queues_confirmation_without_sending_inline(self, mock_queue):
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("book_seats", args=[self.theater.id]),
                {"seats": [str(self.seat1.id), str(self.seat2.id)]},
            )

        self.assertRedirects(response, reverse("profile"), fetch_redirect_response=False)
        self.assertEqual(Booking.objects.count(), 2)
        self.seat1.refresh_from_db()
        self.seat2.refresh_from_db()
        self.assertTrue(self.seat1.is_booked)
        self.assertTrue(self.seat2.is_booked)
        mock_queue.assert_called_once()
        queued_booking_ids, recipient = mock_queue.call_args.args
        self.assertCountEqual(
            queued_booking_ids,
            list(Booking.objects.values_list("id", flat=True)),
        )
        self.assertEqual(recipient, self.user.email)
