from rest_framework import permissions
from datetime import date
from django.utils.timezone import localdate
from music.models import Song
from users.choices import UserTypeChoice

class CanUploadSong(permissions.BasePermission):
    """
    Allows upload if the user has not exceeded their daily upload limit.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user
        today = localdate()
        song_count_today = Song.objects.filter(uploader=user, created_at__date=today).count()

        # Set daily upload limits
        if user.type == UserTypeChoice.BASIC:
            return song_count_today < 10
        elif user.type == UserTypeChoice.PREMIUM:
            return song_count_today < 30
        else:
            return False
