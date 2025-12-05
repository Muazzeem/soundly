import os
import logging
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)


# Firebase credentials path - should be set via environment variable
# Default to the old path for backward compatibility, but should be moved to env var
default_cred_path = os.path.join(
    os.path.dirname(__file__),
    "soundlybeats-firebase-adminsdk-fbsvc-43d2f176b2.json"
)

# Initialize the Firebase app only once
def initialize_firebase_admin(cred_path=None):
    """
    Initializes Firebase Admin SDK with the provided service account key JSON,
    but only if not already initialized.
    
    Args:
        cred_path: Path to Firebase service account JSON file.
                   If None, tries FIREBASE_CREDENTIALS_PATH env var, then default path.
    """
    if not firebase_admin._apps:
        if cred_path is None:
            # Try environment variable first, then default path
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", default_cred_path)
        
        if not os.path.exists(cred_path):
            logger.error(f"Firebase credentials file not found at: {cred_path}")
            logger.warning("FCM notifications will not work without valid Firebase credentials")
            return
        
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin: {e}", exc_info=True)
    else:
        logger.debug("Firebase Admin already initialized.")


def send_push_notification(device_token, title, body, data=None):
    """
    Sends a push notification using the Firebase Admin SDK.

    Args:
        device_token (str): The registration token of the target device.
        title (str): The title of the notification.
        body (str): The body text of the notification.
        data (dict, optional): Additional data payload. Defaults to None.

    Returns:
        str: The message ID from FCM or None if an error occurred.
    """

    # Initialize Firebase Admin SDK
    initialize_firebase_admin()

    # Prepare data payload with string values (Firebase requires string data)
    processed_data = {}
    if data:
        for key, value in data.items():
            processed_data[key] = str(value)

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=processed_data,
        token=device_token,
    )

    try:
        # Send message via Firebase Admin SDK
        response = messaging.send(message)
        logger.info(f'Successfully sent FCM message: {response}')
        return response
    except Exception as e:
        logger.error(f'Error sending FCM message: {e}', exc_info=True)
        return None

