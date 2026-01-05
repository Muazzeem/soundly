from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from core.models import Activity
from music.models import Song, SongExchange
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Song)
def create_song_discovery_activity(sender, instance, created, **kwargs):
    """Create activity when a new song is uploaded (discovery)"""
    if created and instance.uploader:
        try:
            activity = Activity.objects.create(
                actor=instance.uploader,
                activity_type='song_discovery',
                song=instance,
                extra_data={
                    'song_title': instance.title,
                    'song_artist': instance.artist,
                    'song_url': instance.url,
                }
            )
            logger.info(
                f"Created song_discovery activity {activity.uid} for song '{instance.title}' "
                f"by user {instance.uploader.email}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create song_discovery activity for song '{instance.title}': {str(e)}",
                exc_info=True
            )


@receiver(post_save, sender=SongExchange)
def create_song_exchange_activity(sender, instance, created, **kwargs):
    """Create activity when a song exchange is matched"""
    logger.info(
        f"SongExchange signal triggered: exchange_id={instance.uid}, status={instance.status}, "
        f"receiver={instance.receiver.email if instance.receiver else None}, "
        f"received_song={instance.received_song.title if instance.received_song else None}, "
        f"created={created}"
    )
    
    # Only create activities for matched exchanges with a receiver
    if instance.status == 'matched' and instance.receiver and instance.received_song:
        # Check if activity already exists for this exchange
        existing_activity = Activity.objects.filter(
            song_exchange=instance,
            activity_type='song_exchange'
        ).first()
        
        if not existing_activity:
            try:
                # Create ONLY ONE activity per exchange, with the sender as the actor
                # This ensures each exchange appears only once in the feed
                activity = Activity.objects.create(
                    actor=instance.sender,
                    activity_type='song_exchange',
                    song_exchange=instance,
                    extra_data={
                        'sent_song_title': instance.sent_song.title,
                        'sent_song_artist': instance.sent_song.artist,
                        'received_song_title': instance.received_song.title if instance.received_song else None,
                        'received_song_artist': instance.received_song.artist if instance.received_song else None,
                        'receiver_name': instance.receiver.display_name,
                        'sender_name': instance.sender.display_name,
                        'match_type': instance.match_type if instance.match_type else None,
                    }
                )
                logger.info(
                    f"Created single song_exchange activity {activity.uid} for exchange {instance.uid} "
                    f"(sender: {instance.sender.email}, receiver: {instance.receiver.email})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create song_exchange activity for exchange {instance.uid}: {str(e)}",
                    exc_info=True
                )
        else:
            logger.debug(
                f"Skipping activity creation for exchange {instance.uid} - activity already exists"
            )
    else:
        logger.debug(
            f"Skipping activity creation for exchange {instance.uid} - "
            f"status={instance.status}, receiver={bool(instance.receiver)}, "
            f"received_song={bool(instance.received_song)}"
        )

