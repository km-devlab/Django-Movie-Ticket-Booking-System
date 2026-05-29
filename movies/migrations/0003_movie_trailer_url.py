from django.db import migrations, models
import movies.models


class Migration(migrations.Migration):

    dependencies = [
        ("movies", "0002_genre_language_movie_filters"),
    ]

    operations = [
        migrations.AddField(
            model_name="movie",
            name="trailer_url",
            field=models.URLField(blank=True, validators=[movies.models.validate_youtube_trailer_url]),
        ),
    ]
