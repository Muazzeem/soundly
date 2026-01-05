from django.urls import path
from .views import (
    DeleteUserView, UserProfileView, PublicUserProfileView, NotificationToggleView, google_auth, check_daily_upload_limit,
    FriendRequestView, FriendAcceptView, FriendDeclineView, FriendRemoveView,
    FriendsListView, FriendStatusView, PendingFriendRequestsView, UserSearchView
)

urlpatterns = [
    path('user/delete-account/', DeleteUserView.as_view(), name='delete_account'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('users/<uuid:user_id>/', PublicUserProfileView.as_view(), name='public-user-profile'),
    path('notifications/toggle/', NotificationToggleView.as_view(), name='notification-toggle'),
    path('user/check-daily-upload-limit/', check_daily_upload_limit, name='check-daily-upload-limit'),
    path(
        "google/",
        google_auth,
        name="google-auth",
    ),
    # Friends endpoints
    path('friends/request/<uuid:user_id>/', FriendRequestView.as_view(), name='friend-request'),
    path('friends/accept/<uuid:user_id>/', FriendAcceptView.as_view(), name='friend-accept'),
    path('friends/decline/<uuid:user_id>/', FriendDeclineView.as_view(), name='friend-decline'),
    path('friends/<uuid:user_id>/', FriendRemoveView.as_view(), name='friend-remove'),
    path('friends/', FriendsListView.as_view(), name='friends-list'),
    path('friends/status/<uuid:user_id>/', FriendStatusView.as_view(), name='friend-status'),
    path('friends/pending/', PendingFriendRequestsView.as_view(), name='pending-requests'),
    path('users/search/', UserSearchView.as_view(), name='user-search'),
]
