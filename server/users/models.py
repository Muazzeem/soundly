from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.models import BaseUserManager
from core.models import UUIDBaseModel, TimeStampModel
from django.utils.translation import gettext_lazy as _

from .choices import UserTypeChoice

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser, UUIDBaseModel):
    email = models.EmailField(unique=True)
    type = models.CharField(
        _("User Type"),
        max_length=20,
        choices=UserTypeChoice.choices,
        default=UserTypeChoice.BASIC,
    )
    profession = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    device_token = models.CharField(max_length=200, blank=True)
    receive_notifications = models.BooleanField(default=True)
    is_active_for_receiving = models.BooleanField(default=True)

    # Remove username field, use email instead
    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # Fix reverse accessor clashes by customizing related_name
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    objects = CustomUserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_profile(self):
        parts = [self.display_name]
        if self.profession:
            parts.append(self.profession)
        if self.location:
            parts.append(self.location)
        return " • ".join(parts)

    def get_friends(self):
        """Get all accepted friends"""
        friends = Friendship.objects.filter(
            models.Q(requester=self) | models.Q(addressee=self),
            status='accepted'
        ).select_related('requester', 'addressee')
        
        friend_list = []
        for friendship in friends:
            if friendship.requester == self:
                friend_list.append(friendship.addressee)
            else:
                friend_list.append(friendship.requester)
        return friend_list

    def is_friends_with(self, user):
        """Check if users are friends"""
        return Friendship.objects.filter(
            models.Q(requester=self, addressee=user) | models.Q(requester=user, addressee=self),
            status='accepted'
        ).exists()

    def get_friend_status(self, user):
        """Get relationship status with another user"""
        if self == user:
            return 'self'
        
        friendship = Friendship.objects.filter(
            models.Q(requester=self, addressee=user) | models.Q(requester=user, addressee=self)
        ).first()
        
        if not friendship:
            return 'none'
        
        if friendship.status == 'accepted':
            return 'friends'
        elif friendship.requester == self:
            return 'pending_sent'
        else:
            return 'pending_received'


class Friendship(UUIDBaseModel, TimeStampModel):
    """Friendship model for two-way friend relationships"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
    ]
    
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests'
    )
    addressee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_friend_requests'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'friendships'
        unique_together = ('requester', 'addressee')
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['addressee', 'status']),
        ]

    def __str__(self):
        return f"{self.requester.display_name} -> {self.addressee.display_name} ({self.status})"

    def save(self, *args, **kwargs):
        # Prevent self-friendship
        if self.requester == self.addressee:
            raise ValueError("Users cannot be friends with themselves")
        
        # Set accepted_at when status changes to accepted
        if self.status == 'accepted' and not self.accepted_at:
            from django.utils import timezone
            self.accepted_at = timezone.now()
        
        super().save(*args, **kwargs)
