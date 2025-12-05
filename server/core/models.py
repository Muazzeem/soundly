import uuid

from django.db import models


class BaseModel(models.Model):
    class Meta:
        abstract = True


class UUIDBaseModel(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True)

    class Meta:
        abstract = True


class TimeStampModel(BaseModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActiveTimeStampModel(TimeStampModel):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class ActiveObjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Activity(UUIDBaseModel, TimeStampModel):
    """
    Activity feed model for tracking user activities
    """
    ACTIVITY_TYPES = [
        ('song_exchange', 'Song Exchange'),
        ('song_discovery', 'Song Discovery'),
    ]
    
    actor = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES
    )
    
    # For song exchange
    song_exchange = models.ForeignKey(
        'music.SongExchange',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    
    # For song discovery (new song upload)
    song = models.ForeignKey(
        'music.Song',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discovery_activities'
    )
    
    # Additional data stored as JSON
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actor', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.actor.display_name} - {self.get_activity_type_display()}"


class ActivityReaction(UUIDBaseModel, TimeStampModel):
    """
    Reactions to activities (musical notes instead of likes)
    """
    REACTION_TYPES = [
        ('🎵', 'Musical Note'),
        ('🎶', 'Musical Notes'),
        ('🎸', 'Guitar'),
        ('🎹', 'Piano'),
        ('🥁', 'Drum'),
        ('🎤', 'Microphone'),
    ]
    
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_TYPES,
        default='🎵'
    )

    class Meta:
        db_table = 'activity_reactions'
        unique_together = ('user', 'activity', 'reaction_type')
        indexes = [
            models.Index(fields=['activity', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.display_name} {self.reaction_type} on {self.activity}"


class ActivityComment(UUIDBaseModel, TimeStampModel):
    """
    Comments on activities
    """
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='activity_comments'
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    text = models.TextField(max_length=500)

    class Meta:
        db_table = 'activity_comments'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['activity', 'created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.display_name} commented on {self.activity}"