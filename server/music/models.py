from django.db import models
from django.core.validators import URLValidator
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, F, Func
from django.utils.timezone import localdate

from users.choices import UserTypeChoice

User = get_user_model()

from core.models import UUIDBaseModel, TimeStampModel


class MusicPlatform(UUIDBaseModel):
    """
    Supported music platforms (Spotify, YouTube, Apple Music, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    domain = models.CharField(max_length=100, unique=True)
    icon = models.ImageField(upload_to='platform_icons/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'music_platforms'
        ordering = ['name']

    def __str__(self):
        return self.name


class Song(UUIDBaseModel, TimeStampModel):
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    platform = models.ForeignKey(MusicPlatform, on_delete=models.CASCADE)
    genre = models.JSONField(default=list, blank=True)
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    album = models.CharField(max_length=200, blank=True)
    url = models.URLField(validators=[URLValidator()])
    fun_fact = models.TextField(blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    release_date = models.CharField(null=True, blank=True)
    cover_image_url = models.URLField(blank=True)


    def __str__(self):
        return f"{self.title} by {self.artist}"

    class Meta:
        db_table = 'songs'
        indexes = [
            models.Index(fields=['genre']),
            models.Index(fields=['artist']),
            models.Index(fields=['created_at']),
        ]

    @property
    def remaining_uploads(self):
        """
        Returns the number of uploads remaining for today based on user type.
        BASIC: 20/day
        Others: Unlimited
        """
        if not self.uploader or not self.uploader.is_authenticated:
            return 0

        if self.uploader.type == UserTypeChoice.BASIC:
            today = localdate()
            uploaded_today = Song.objects.filter(
                uploader=self.uploader, created_at__date=today
            ).count()
            return max(0, 20 - uploaded_today)
        return float("inf")


class SongExchange(UUIDBaseModel, TimeStampModel):
    """
    Tracks song exchanges between users
    """
    EXCHANGE_STATUS = [
        ('pending', 'Pending Match'),
        ('matched', 'Matched'),
        ('completed', 'Completed'),
    ]

    sender = models.ForeignKey(User, related_name='sent_songs', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_songs', on_delete=models.CASCADE, null=True, blank=True)
    sent_song = models.ForeignKey(Song, related_name='sent_exchanges', on_delete=models.CASCADE)
    received_song = models.ForeignKey(Song, related_name='received_exchanges', on_delete=models.CASCADE, null=True, blank=True)

    status = models.CharField(max_length=20, choices=EXCHANGE_STATUS, default='pending')
    matched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        db_table = 'song_exchanges'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['receiver', 'created_at']),
        ]
