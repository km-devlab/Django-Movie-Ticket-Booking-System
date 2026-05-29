from django.db import migrations


TRAILER_URLS = {
    "Avatar: The Way of Water": "https://www.youtube.com/watch?v=d9MyW72ELq0",
    "Avengers: Endgame": "https://www.youtube.com/watch?v=TcMBFSGVi1c",
    "Black Panther": "https://www.youtube.com/watch?v=xjDjIWPwcPU",
    "Coco": "https://www.youtube.com/watch?v=Ga6RYejo6Hk",
    "Interstellar": "https://www.youtube.com/watch?v=zSWdZVtXT7E",
    "Spider-Man: Into the Spider-Verse": "https://www.youtube.com/watch?v=g4Hbz2jLxvQ",
    "The Dark Knight": "https://www.youtube.com/watch?v=EXeTwQWrcwY",
    "The Lion King": "https://www.youtube.com/watch?v=7TavVZMewpY",
}


def seed_sample_trailers(apps, schema_editor):
    Movie = apps.get_model("movies", "Movie")
    for movie_name, trailer_url in TRAILER_URLS.items():
        Movie.objects.filter(name=movie_name, trailer_url="").update(trailer_url=trailer_url)


def clear_sample_trailers(apps, schema_editor):
    Movie = apps.get_model("movies", "Movie")
    for movie_name, trailer_url in TRAILER_URLS.items():
        Movie.objects.filter(name=movie_name, trailer_url=trailer_url).update(trailer_url="")


class Migration(migrations.Migration):

    dependencies = [
        ("movies", "0003_movie_trailer_url"),
    ]

    operations = [
        migrations.RunPython(seed_sample_trailers, clear_sample_trailers),
    ]
