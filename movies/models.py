from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError
from django.contrib.auth.models import User 
from django.db import models


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


def extract_youtube_video_id(url):
    parsed_url = urlparse(url.strip())
    host = parsed_url.netloc.lower()

    if host not in YOUTUBE_HOSTS:
        return None

    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed_url.path.strip("/").split("/")[0]
    elif parsed_url.path == "/watch":
        video_id = parse_qs(parsed_url.query).get("v", [""])[0]
    elif parsed_url.path.startswith("/embed/"):
        video_id = parsed_url.path.split("/embed/", 1)[1].split("/")[0]
    elif parsed_url.path.startswith("/shorts/"):
        video_id = parsed_url.path.split("/shorts/", 1)[1].split("/")[0]
    else:
        return None

    if len(video_id) == 11 and all(char.isalnum() or char in "_-" for char in video_id):
        return video_id
    return None


def validate_youtube_trailer_url(url):
    if url and not extract_youtube_video_id(url):
        raise ValidationError("Enter a valid YouTube trailer URL.")


class Movie(models.Model):
    name= models.CharField(max_length=255)
    image= models.ImageField(upload_to="movies/")
    rating = models.DecimalField(max_digits=3,decimal_places=1)
    cast= models.TextField()
    description= models.TextField(blank=True,null=True) # optional
    trailer_url = models.URLField(blank=True, validators=[validate_youtube_trailer_url])
    genres = models.ManyToManyField("Genre", related_name="movies", blank=True)
    languages = models.ManyToManyField("Language", related_name="movies", blank=True)

    def __str__(self):
        return self.name

    @property
    def youtube_embed_url(self):
        video_id = extract_youtube_video_id(self.trailer_url or "")
        if not video_id:
            return ""
        return f"https://www.youtube-nocookie.com/embed/{video_id}"

    class Meta:
        indexes = [
            models.Index(fields=["name"], name="movie_name_idx"),
            models.Index(fields=["rating", "name"], name="movie_rating_name_idx"),
        ]


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"], name="genre_slug_idx"),
        ]

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"], name="language_slug_idx"),
        ]

    def __str__(self):
        return self.name

class Theater(models.Model):
    name = models.CharField(max_length=255)
    movie = models.ForeignKey(Movie,on_delete=models.CASCADE,related_name='theaters')
    time= models.DateTimeField()

    def __str__(self):
        return f'{self.name} - {self.movie.name} at {self.time}'

class Seat(models.Model):
    theater = models.ForeignKey(Theater,on_delete=models.CASCADE,related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked=models.BooleanField(default=False)

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'

class Booking(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    seat=models.OneToOneField(Seat,on_delete=models.CASCADE)
    movie=models.ForeignKey(Movie,on_delete=models.CASCADE)
    theater=models.ForeignKey(Theater,on_delete=models.CASCADE)
    booked_at=models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f'Booking by{self.user.username} for {self.seat.seat_number} at {self.theater.name}'


class EmailTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    error_message = models.TextField(blank=True, null=True)
    payment_id = models.CharField(max_length=100)
    retry_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Email to {self.recipient} (Status: {self.status}, Payment ID: {self.payment_id})"

