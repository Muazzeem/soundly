from rest_framework import permissions
from music.models import Song

class CanUploadSong(permissions.BasePermission):
    """
    Allows upload if the user has not exceeded their daily upload limit.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        temp_song = Song(uploader=user)
        if temp_song.remaining_uploads <= 0:
            self.message = f"Upload limit reached. You have {temp_song.remaining_uploads} uploads remaining."
            return False

        return True
