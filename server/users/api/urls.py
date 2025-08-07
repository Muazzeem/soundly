from django.urls import path
from .views import DeleteUserView, UserProfileView, NotificationToggleView, google_auth

urlpatterns = [
    path('user/delete-account/', DeleteUserView.as_view(), name='delete_account'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('notifications/toggle/', NotificationToggleView.as_view(), name='notification-toggle'),
    path(
        "google/",
        google_auth,
        name="google-auth",
    ),
]
