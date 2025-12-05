from rest_framework import generics
from rest_framework.response import Response
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from notifications.models import Notification
from music.api.views import SongExchangePagination
from .serializers import NotificationHQSerializer



class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationHQSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SongExchangePagination

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-timestamp')


class UnreadNotificationListView(generics.ListAPIView):
    serializer_class = NotificationHQSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.unread().order_by('-timestamp')


class ReadNotificationListView(generics.ListAPIView):
    serializer_class = NotificationHQSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.read().order_by('-timestamp')


class NotificationDetailView(generics.RetrieveAPIView):
    serializer_class = NotificationHQSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class UnreadNotificationsCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        unread_count = request.user.notifications.unread().count()

        return Response({
            'count': unread_count
        })


class MarkAsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_as_read()
        return Response({'detail': 'Marked as read'})


class MarkAllAsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.notifications.unread().mark_all_as_read()
        return Response({'detail': 'All unread notifications marked as read'})


class MarkAllAsUnreadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.notifications.read().mark_all_as_unread()
        return Response({'detail': 'All read notifications marked as unread'})


class DeleteNotificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.deleted()
        return Response({'detail': 'Notification soft deleted'})


class MarkAllAsDeletedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        notifications = request.user.notifications.read()
        count = notifications.update(deleted=True)

        return Response({
            'detail': f'{count} notifications marked as deleted'
        })
