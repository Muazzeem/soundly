import os
import firebase_admin
from firebase_admin import credentials, messaging


file_path = os.path.join(os.path.dirname(__file__),
                "soundlybeats-firebase-adminsdk-fbsvc-43d2f176b2.json"
            )


# Initialize the Firebase app only once
def initialize_firebase_admin(cred_path=file_path):
    """
    Initializes Firebase Admin SDK with the provided service account key JSON,
    but only if not already initialized.
    """
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize Firebase Admin: {e}")
    else:
        print("Firebase Admin already initialized.")


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
        print(f'Successfully sent message: {response}')
        return response
    except Exception as e:
        print(f'Error sending message: {e}')
        return None

