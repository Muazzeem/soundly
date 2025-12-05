from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Friendship


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model"""
    list_display = ('email', 'first_name', 'last_name', 'type', 'is_staff', 'is_active', 'created_at')
    list_filter = ('type', 'is_staff', 'is_active', 'is_superuser', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'profession', 'city', 'country')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'uid')
    
    fieldsets = (
        (None, {'fields': ('email', 'password', 'uid')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'profession', 'country', 'city', 'profile_image')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'type', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
        ('Notifications', {'fields': ('device_token', 'receive_notifications', 'is_active_for_receiving')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'type'),
        }),
    )


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    """Admin for Friendship model"""
    list_display = ('requester', 'addressee', 'status', 'created_at', 'accepted_at')
    list_filter = ('status', 'created_at', 'accepted_at')
    search_fields = ('requester__email', 'addressee__email', 'requester__first_name', 'addressee__first_name')
    readonly_fields = ('created_at', 'updated_at', 'uid', 'accepted_at')
    ordering = ('-created_at',)
