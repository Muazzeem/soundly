import os
import logging
from django.contrib.auth import get_user_model


from notifications.signals import notify
from notifications.models import Notification as NotificationModel

# Set up logging
logger = logging.getLogger(__name__)
User = get_user_model()


def send_notification(
    sender, recipient, verb, action_object=None, target=None, description=None,
    send_push=True,
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
                logger.warning("Admin user not found, using system user")
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
        )
        device_token = User.objects.get(email=recipient.email).device_token
        try:
            notification = NotificationModel.objects.filter(
                recipient=recipient
            ).order_by('-timestamp').first()

            if notification:
                payload = {}
                if notification.target_content_type:
                    payload["target_content_type"] = {
                        "model": notification.target_content_type.model,
                        "target_object_id": str(notification.target_object_id),
                        "notification_id": str(notification.id),
                    }

                # Additional data you might want to include
                if notification.id:
                    payload["notification_id"] = str(notification.id)

                # Send the push notification
                if device_token:
                    pass
                else:
                    logger.warning(f"No device token available for user {recipient.username}")
        except Exception as e:
            logger.error(f"Error preparing push notification: {e}")
            # Continue execution - don't fail the entire notification process
            # if push notification fails

        return True
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False
