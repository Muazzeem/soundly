from django.contrib import admin
from .models import Activity, ActivityReaction, ActivityComment


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    """Admin for Activity model"""
    list_display = ('actor', 'activity_type', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('actor__email', 'actor__first_name', 'actor__last_name')
    readonly_fields = ('created_at', 'updated_at', 'uid')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'


@admin.register(ActivityReaction)
class ActivityReactionAdmin(admin.ModelAdmin):
    """Admin for ActivityReaction model"""
    list_display = ('user', 'activity', 'reaction_type', 'created_at')
    list_filter = ('reaction_type', 'created_at')
    search_fields = ('user__email', 'activity__actor__email')
    readonly_fields = ('created_at', 'updated_at', 'uid')
    ordering = ('-created_at',)


@admin.register(ActivityComment)
class ActivityCommentAdmin(admin.ModelAdmin):
    """Admin for ActivityComment model"""
    list_display = ('user', 'activity', 'text', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'text', 'activity__actor__email')
    readonly_fields = ('created_at', 'updated_at', 'uid')
    ordering = ('-created_at',)
