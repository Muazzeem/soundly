from django.urls import path, include
from .views import *
urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('unread-notifications/', UnreadNotificationListView.as_view(), name='unread-notifications'),
    path('read-notifications/', ReadNotificationListView.as_view(), name='read-notifications'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('unread-notifications/count/', UnreadNotificationsCountView.as_view(), name='unread-notifications-count'),
    path('notifications/mark-as-read/<int:pk>/', MarkAsReadView.as_view(), name='mark-as-read'),
    path('notifications/mark-all-as-read/', MarkAllAsReadView.as_view(), name='mark-all-as-read'),
    path('notifications/mark-all-as-unread/', MarkAllAsUnreadView.as_view(), name='mark-all-as-unread'),
]

app_name = 'notifications'

