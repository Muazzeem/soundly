from django.contrib.auth import get_user_model


from notifications.signals import notify
from notifications.models import Notification as NotificationModel

from .fcm_notification import send_push_notification
User = get_user_model()


def send_notification(
    sender, recipient, verb, action_object=None, target=None, description=None,
    send_push=False, target_url=None
):
    """
    Send a notification through Django's notification system and optionally as a push notification.
    """
    try:
        # Use admin user as fallback sender if not provided
        if sender is None:
            try:
                sender = User.objects.get(email="admin@soundlybeats.com")
            except User.DoesNotExist:
                sender, created = User.objects.get_or_create(
                    first_name="system",
                    defaults={"email": "system@soundlybeats.com", "is_active": False}
                )

        notify.send(
            sender=sender,
            recipient=recipient,
            verb=verb,
            action_object=action_object,
            target=target,
            description=description,
            public=False,
            extra_data={"song_url": target_url}
        )

        device_token = User.objects.get(email=recipient.email).device_token
        if not device_token:
            return False
        else:
            if send_push:
                send_push_notification(
                    device_token,
                    "Your song was uploaded successfully",
                    "Please check your library to see your match song",
                )


        return True
    except Exception as e:
        return False
