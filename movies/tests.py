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
