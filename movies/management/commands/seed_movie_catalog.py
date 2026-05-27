from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils.text import slugify

from movies.models import Genre, Language, Movie


REAL_MOVIES = [
    ("A Quiet Place: Part II", "A QUIET PLACE_ PART II (2021).jpg", "Horror thriller sequel with a family surviving in silence.", ["Horror", "Thriller"], ["English"], "Emily Blunt, Cillian Murphy", "7.2"),
    ("Aladdin", "Aladdin.jpg", "A street-smart dreamer discovers a magical lamp and a bigger destiny.", ["Fantasy", "Adventure", "Musical"], ["English"], "Will Smith, Mena Massoud, Naomi Scott", "6.9"),
    ("Avatar: The Way of Water", "Avatar The Way of Water.jpg", "The Sully family explores new oceans and old conflicts on Pandora.", ["Sci-Fi", "Adventure"], ["English"], "Sam Worthington, Zoe Saldana", "7.6"),
    ("Avengers: Endgame", "Avengers Endgame.jpg", "Earth's heroes make a final stand after the snap.", ["Action", "Adventure", "Sci-Fi"], ["English"], "Robert Downey Jr., Chris Evans, Scarlett Johansson", "8.4"),
    ("Baby's Day Out", "Baby's Day Out.jpg", "A baby wanders through the city while kidnappers fail spectacularly.", ["Comedy", "Family"], ["English"], "Joe Mantegna, Lara Flynn Boyle", "6.2"),
    ("Black Panther", "Black Panther.jpg", "A new king protects Wakanda while facing a challenger with a painful past.", ["Action", "Adventure"], ["English"], "Chadwick Boseman, Michael B. Jordan", "7.3"),
    ("Coco", "Coco.jpg", "A young musician journeys through the Land of the Dead.", ["Animation", "Family", "Musical"], ["English"], "Anthony Gonzalez, Gael Garcia Bernal", "8.4"),
    ("Dead Poets Society", "DeadPoetsSociety.jpg", "An inspiring teacher urges students to think and live boldly.", ["Drama"], ["English"], "Robin Williams, Ethan Hawke", "8.1"),
    ("Soul", "Disney SOUL.jpg", "A jazz pianist discovers what makes life meaningful.", ["Animation", "Comedy", "Family"], ["English"], "Jamie Foxx, Tina Fey", "8.0"),
    ("Gone Girl", "Gone Girl.jpg", "A missing-person case turns into a media storm and a twisted mystery.", ["Thriller", "Mystery"], ["English"], "Ben Affleck, Rosamund Pike", "8.1"),
    ("Good Will Hunting", "good will hunting.jpg", "A gifted janitor faces his past and his future.", ["Drama"], ["English"], "Matt Damon, Robin Williams", "8.3"),
    ("Grave of the Fireflies", "Grave of Fireflies.jpg", "Two siblings struggle to survive during wartime Japan.", ["Animation", "Drama"], ["Japanese"], "Tsutomu Tatsumi, Ayano Shiraishi", "8.5"),
    ("How To Train Your Dragon", "How To Train Your Dragon.jpg", "A young Viking befriends a dragon and changes his village.", ["Animation", "Adventure", "Family"], ["English"], "Jay Baruchel, Gerard Butler", "8.1"),
    ("Inside Out", "Inside Out _ movie poster.jpg", "A girl's emotions guide her through a difficult move.", ["Animation", "Comedy", "Family"], ["English"], "Amy Poehler, Phyllis Smith", "8.1"),
    ("Interstellar", "Interstellar.jpg", "Explorers cross space and time to find humanity a future.", ["Sci-Fi", "Drama"], ["English"], "Matthew McConaughey, Anne Hathaway", "8.7"),
    ("It Chapter Two", "IT Chapter II.jpg", "The Losers Club returns to face an old terror.", ["Horror", "Drama"], ["English"], "James McAvoy, Jessica Chastain", "6.5"),
    ("Kiki's Delivery Service", "Kiki’s Delivery Service (1989).jpg", "A young witch starts an airborne delivery business.", ["Animation", "Family", "Fantasy"], ["Japanese"], "Minami Takayama, Rei Sakuma", "7.8"),
    ("La La Land", "La La Land.jpg", "Two artists fall in love while chasing their dreams in Los Angeles.", ["Musical", "Romance", "Drama"], ["English"], "Ryan Gosling, Emma Stone", "8.0"),
    ("Life of Pi", "Life Of Pi.jpg", "A survivor shares a wondrous story of faith, fear, and the sea.", ["Adventure", "Drama"], ["English"], "Suraj Sharma, Irrfan Khan", "7.9"),
    ("Pride & Prejudice", "pride & prejudice.jpg", "Elizabeth Bennet and Mr. Darcy test pride, class, and affection.", ["Romance", "Drama"], ["English"], "Keira Knightley, Matthew Macfadyen", "7.8"),
    ("Shawshank Redemption", "Shawshank Redemption.jpg", "Two prisoners find friendship and hope across decades.", ["Drama"], ["English"], "Tim Robbins, Morgan Freeman", "9.3"),
    ("Spider-Man: Into the Spider-Verse", "Spider-Man_ Into the Spider-Verse.jpg", "Miles Morales discovers a universe full of Spider-heroes.", ["Animation", "Action", "Adventure"], ["English"], "Shameik Moore, Hailee Steinfeld", "8.4"),
    ("The Boy in the Striped Pajamas", "The Boy in the Striped Pajamas.jpg", "A childhood friendship unfolds beside history's cruelty.", ["Drama", "War"], ["English"], "Asa Butterfield, Vera Farmiga", "7.7"),
    ("The Conjuring", "The Conjuring Movie Poster.jpg", "Paranormal investigators face a terrifying haunting.", ["Horror", "Mystery"], ["English"], "Patrick Wilson, Vera Farmiga", "7.5"),
    ("The Dark Knight", "The Dark Knight.jpg", "Batman faces the Joker in a battle for Gotham's soul.", ["Action", "Crime", "Drama"], ["English"], "Christian Bale, Heath Ledger", "9.0"),
    ("The Intern", "The Intern.jpg", "A retired widower becomes an intern at a fashion startup.", ["Comedy", "Drama"], ["English"], "Robert De Niro, Anne Hathaway", "7.1"),
    ("The Lion King", "The Lion King.jpg", "A young lion prince grows into his place in the circle of life.", ["Animation", "Adventure", "Family"], ["English"], "Donald Glover, Beyonce", "6.8"),
    ("The Martian", "The Martian.jpg", "An astronaut stranded on Mars engineers his way toward rescue.", ["Sci-Fi", "Adventure", "Drama"], ["English"], "Matt Damon, Jessica Chastain", "8.0"),
    ("The Pursuit of Happyness", "The Pursuit of Happyness.jpg", "A struggling father fights to build a better life for his son.", ["Drama"], ["English"], "Will Smith, Jaden Smith", "8.0"),
    ("The Truman Show", "The Truman Show.jpg", "A man discovers his entire life may be a television production.", ["Comedy", "Drama", "Sci-Fi"], ["English"], "Jim Carrey, Laura Linney", "8.2"),
    ("Up", "Up.jpg", "An old dreamer and a young scout lift off toward adventure.", ["Animation", "Adventure", "Family"], ["English"], "Ed Asner, Jordan Nagai", "8.3"),
    ("Whisper of the Heart", "whisper of the heart.jpg", "A young writer finds inspiration, love, and creative courage.", ["Animation", "Drama", "Romance"], ["Japanese"], "Yoko Honna, Issey Takahashi", "7.8"),
    ("Wonder", "Wonder.jpg", "A boy with facial differences starts school and changes his community.", ["Drama", "Family"], ["English"], "Jacob Tremblay, Julia Roberts", "7.9"),
]

GENRES = sorted({genre for movie in REAL_MOVIES for genre in movie[3]} | {"Crime", "War"})
LANGUAGES = sorted({language for movie in REAL_MOVIES for language in movie[4]} | {"Hindi", "Tamil", "Telugu"})


class Command(BaseCommand):
    help = "Seed a realistic movie catalog and optionally add unique synthetic rows for scale testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=0,
            help="Total number of movies desired after seeding. Use 5000 for scale testing.",
        )
        parser.add_argument(
            "--real-only",
            action="store_true",
            help="Only seed the real poster-backed movies.",
        )

    def handle(self, *args, **options):
        self._seed_facets()
        created_real = self._seed_real_movies()
        self._remove_unused_seed_facets()

        synthetic_created = 0
        if not options["real_only"] and options["count"] > Movie.objects.count():
            synthetic_created = self._seed_synthetic_movies(options["count"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {Movie.objects.count()} movies, "
                f"{Genre.objects.count()} genres, {Language.objects.count()} languages. "
                f"Real created/updated: {created_real}. Synthetic created: {synthetic_created}."
            )
        )

    def _seed_facets(self):
        for genre in GENRES:
            Genre.objects.update_or_create(slug=slugify(genre), defaults={"name": genre})
        for language in LANGUAGES:
            Language.objects.update_or_create(slug=slugify(language), defaults={"name": language})

    def _seed_real_movies(self):
        saved = 0
        for title, poster, description, genres, languages, cast, rating in REAL_MOVIES:
            movie, _ = Movie.objects.update_or_create(
                name=title,
                defaults={
                    "image": f"movies/{poster}",
                    "rating": Decimal(rating),
                    "cast": cast,
                    "description": description,
                },
            )
            movie.genres.set(Genre.objects.filter(name__in=genres))
            movie.languages.set(Language.objects.filter(name__in=languages))
            saved += 1
        return saved

    def _seed_synthetic_movies(self, desired_total):
        posters = [movie[1] for movie in REAL_MOVIES if Path("media", "movies", movie[1]).exists()]
        if not posters:
            posters = [movie[1] for movie in REAL_MOVIES]

        genres = list(Genre.objects.all())
        languages = list(Language.objects.all())
        existing = Movie.objects.count()
        to_create = desired_total - existing
        batch = []

        for index in range(existing + 1, desired_total + 1):
            rating = Decimal(f"{5 + (index % 45) / 10:.1f}")
            batch.append(
                Movie(
                    name=f"Catalog Test Movie {index:05d}",
                    image=f"movies/{posters[index % len(posters)]}",
                    rating=rating,
                    cast=f"Actor {index % 97}, Actor {(index + 17) % 97}",
                    description="Synthetic catalog row for server-side filtering and pagination testing.",
                )
            )

        Movie.objects.bulk_create(batch, batch_size=500)

        synthetic_movies = Movie.objects.order_by("-id")[:to_create]
        through_genres = Movie.genres.through
        through_languages = Movie.languages.through
        genre_links = []
        language_links = []

        for offset, movie in enumerate(synthetic_movies):
            first_genre = genres[offset % len(genres)]
            second_genre = genres[(offset + 3) % len(genres)]
            language = languages[offset % len(languages)]
            genre_links.append(through_genres(movie_id=movie.id, genre_id=first_genre.id))
            if second_genre.id != first_genre.id:
                genre_links.append(through_genres(movie_id=movie.id, genre_id=second_genre.id))
            language_links.append(through_languages(movie_id=movie.id, language_id=language.id))

        through_genres.objects.bulk_create(genre_links, batch_size=1000, ignore_conflicts=True)
        through_languages.objects.bulk_create(language_links, batch_size=1000, ignore_conflicts=True)
        return to_create

    def _remove_unused_seed_facets(self):
        allowed_genre_slugs = {slugify(genre) for genre in GENRES}
        allowed_language_slugs = {slugify(language) for language in LANGUAGES}
        Genre.objects.annotate(movie_total=Count("movies")).filter(movie_total=0).exclude(
            slug__in=allowed_genre_slugs
        ).delete()
        Language.objects.annotate(movie_total=Count("movies")).filter(movie_total=0).exclude(
            slug__in=allowed_language_slugs
        ).delete()
