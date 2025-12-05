from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from core.models import Activity
from music.models import Song, SongExchange

User = get_user_model()


@receiver(post_save, sender=Song)
def create_song_discovery_activity(sender, instance, created, **kwargs):
    """Create activity when a new song is uploaded (discovery)"""
    if created and instance.uploader:
        Activity.objects.create(
            actor=instance.uploader,
            activity_type='song_discovery',
            song=instance,
            extra_data={
                'song_title': instance.title,
                'song_artist': instance.artist,
                'song_url': instance.url,
            }
        )


@receiver(post_save, sender=SongExchange)
def create_song_exchange_activity(sender, instance, created, **kwargs):
    """Create activity when a song exchange is matched"""
    # Only create activities for matched exchanges with a receiver
    if instance.status == 'matched' and instance.receiver and instance.received_song:
        # Check if activities already exist for this exchange
        existing_activities = Activity.objects.filter(
            song_exchange=instance,
            activity_type='song_exchange'
        )
        
        if not existing_activities.exists():
            # Create activity for the sender
            Activity.objects.create(
                actor=instance.sender,
                activity_type='song_exchange',
                song_exchange=instance,
                extra_data={
                    'sent_song_title': instance.sent_song.title,
                    'sent_song_artist': instance.sent_song.artist,
                    'received_song_title': instance.received_song.title if instance.received_song else None,
                    'received_song_artist': instance.received_song.artist if instance.received_song else None,
                    'receiver_name': instance.receiver.display_name,
                }
            )
            
            # Create activity for the receiver
            Activity.objects.create(
                actor=instance.receiver,
                activity_type='song_exchange',
                song_exchange=instance,
                extra_data={
                    'sent_song_title': instance.received_song.title if instance.received_song else None,
                    'sent_song_artist': instance.received_song.artist if instance.received_song else None,
                    'received_song_title': instance.sent_song.title,
                    'received_song_artist': instance.sent_song.artist,
                    'sender_name': instance.sender.display_name,
                }
            )

