from datetime import timedelta
from django.utils import timezone

from rest_framework import serializers
from notifications.models import Notification
from django.contrib.contenttypes.models import ContentType


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'model']

class NotificationHQSerializer(serializers.ModelSerializer):
    target_content_type = ContentTypeSerializer(read_only=True)
    created_ago = serializers.SerializerMethodField()
    song_url = serializers.SerializerMethodField()
    activity_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = '__all__'


    def get_created_ago(self, obj):
        now = timezone.now()
        time_difference = now - obj.timestamp

        if time_difference < timedelta(minutes=1):
            return "just now"
        elif time_difference < timedelta(hours=1):
            minutes = int(time_difference.total_seconds() // 60)
            return f"{minutes} min ago"
        elif time_difference < timedelta(days=1):
            hours = int(time_difference.total_seconds() // 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            days = time_difference.days
            return f"{days} day{'s' if days > 1 else ''} ago"

    def get_song_url(self, obj):
        if obj.data:
            return obj.data.get('extra_data', {}).get('song_url')
        else:
            return None

    def get_activity_id(self, obj):
        if obj.data:
            return obj.data.get('extra_data', {}).get('activity_id')
        else:
            return None
