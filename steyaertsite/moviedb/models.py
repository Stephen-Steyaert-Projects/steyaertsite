from django.db import models
import uuid

RATING_CHOICES = [
    ('G', 'G'),
    ('PG', 'PG'),
    ('PG-13', 'PG-13'),
    ('R', 'R'),
    ('NR', 'NR'),
    ('TV', 'TV'),
]

DISK_CHOICES = [
    ('4k', '4K Ultra HD'),
    ('blu-ray', 'Blu-Ray'),
    ('dvd', 'DVD'),
]

class Movie(models.Model):
    class Meta:
        unique_together = ('title', 'rating', 'disk')

    title = models.CharField(max_length=200)
    rating = models.CharField(max_length=6, choices=RATING_CHOICES)
    disk = models.CharField(max_length=8, choices=DISK_CHOICES)

    def __str__(self):
        return f"{self.title}"


class RandomMovieResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    movies = models.JSONField()  # List of dicts: [{"title": "Movie Name", "rating": "PG"}, ...]

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),  # For efficient purge queries
        ]

    def __str__(self):
        return f"Random result {self.id} ({len(self.movies)} movies)"