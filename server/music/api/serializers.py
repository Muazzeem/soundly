from rest_framework import serializers
from music.models import Song, MusicPlatform, SongExchange
from users.api.serializers import UserSerializer


class MusicPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicPlatform
        fields = ['uid', 'name', 'domain']


class SongSerializer(serializers.ModelSerializer):
    platform = MusicPlatformSerializer(read_only=True)
    uploader = UserSerializer(read_only=True)

    class Meta:
        model = Song
        fields = [
            'uid', 'title', 'artist', 'album', 'genre', 'url',
            'duration_seconds', 'release_date', 'cover_image_url',
            'platform', 'uploader', 'created_at', 'updated_at'
        ]


class SongCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = [
            'title', 'artist', 'album', 'genre', 'url',
            'duration_seconds', 'release_date', 'cover_image_url',
            'platform', 'uploader'
        ]


class SongExchangeSerializer(serializers.ModelSerializer):
    sent_song = SongSerializer(read_only=True)
    received_song = SongSerializer(read_only=True)
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    receiver_email = serializers.CharField(source='receiver.email', read_only=True)

    class Meta:
        model = SongExchange
        fields = [
            'uid', 'sender', 'receiver', 'sent_song', 'received_song',
            'status', 'matched_at', 'completed_at', 'created_at',
            'sender_email', 'receiver_email'
        ]



class MatchedSongExchangeSerializer(serializers.ModelSerializer):
    received_song = SongSerializer()
    sender = UserSerializer()

    class Meta:
        model = SongExchange
        fields = ['id', 'sent_song', 'received_song', 'matched_at', 'sender']
