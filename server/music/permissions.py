from rest_framework import permissions
from datetime import date
from django.utils.timezone import localdate
from music.models import Song
from users.choices import UserTypeChoice
from django.conf import settings

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

        if user.type == UserTypeChoice.BASIC:
            return song_count_today < settings.SONG_UPLOAD_LIMIT
        
        elif user.type == UserTypeChoice.PREMIUM:
            pass

        elif user.type == UserTypeChoice.ARTIST:
            pass

        elif user.type == UserTypeChoice.INFLUENCER:
            pass

        else:
            return False
