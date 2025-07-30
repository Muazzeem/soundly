from django.contrib import admin
from .models import MusicPlatform, Song, SongExchange


@admin.register(MusicPlatform)
class MusicPlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'domain')
    ordering = ('name',)


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'platform', 'genre', 'release_date', 'created_at')
    list_filter = ('platform', 'release_date', 'genre')
    search_fields = ('title', 'artist', 'album')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SongExchange)
class SongExchangeAdmin(admin.ModelAdmin):
    list_display = (
        'sent_song_title', 'received_song_title',
        'status', 'matched_at', 'created_at'
    )
    list_filter = ('status', 'created_at', 'matched_at')
    search_fields = ('sender__email', 'receiver__email', 'sent_song__title', 'received_song__title')
    readonly_fields = ('matched_at', 'completed_at', 'created_at', 'updated_at')


    def sent_song_title(self, obj):
        return obj.sent_song.title

    def received_song_title(self, obj):
        return obj.received_song.title if obj.received_song else '—'
