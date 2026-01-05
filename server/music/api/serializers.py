from rest_framework import serializers
from music.models import Song, MusicPlatform, SongExchange
from users.choices import UserTypeChoice
from users.api.serializers import UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class MusicPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicPlatform
        fields = ['uid', 'name', 'domain']


class SongUploaderSerializer(serializers.ModelSerializer):
    """Serializer for song uploader with profile image URL"""
    name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'email',
            'name',
            'profession',
            'country',
            'city',
            'profile_image',
            'type',
        ]
    
    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_profile_image(self, obj):
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
        return None


class SongSerializer(serializers.ModelSerializer):
    platform = MusicPlatformSerializer(read_only=True)
    uploader = SongUploaderSerializer(read_only=True)
    remaining_uploads = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = [
            'uid', 'remaining_uploads', 'title', 'artist', 'album', 'genre', 'url', 'fun_fact',
            'duration_seconds', 'release_date', 'cover_image_url',
            'platform', 'uploader', 'created_at', 'updated_at'
        ]

    def get_remaining_uploads(self, obj):
        if obj.uploader and obj.uploader.type == UserTypeChoice.BASIC:
            return obj.remaining_uploads
        return None


class SongCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = [
            'title', 'artist', 'album', 'genre', 'url', 'fun_fact',
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
    sent_song = SongSerializer()
    sender = UserSerializer()
    receiver = UserSerializer()

    class Meta:
        model = SongExchange
        fields = ['id', 'sent_song', 'received_song', 'matched_at', 'sender', 'receiver']
