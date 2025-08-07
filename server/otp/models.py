from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import random

from core.models import TimeStampModel

User = get_user_model()


class OTPValidation(TimeStampModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.otp}"

    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP"""
        return "".join([str(random.randint(0, 9)) for _ in range(6)])

    def is_expired(self, expiry_minutes=10):
        """Check if OTP is expired (default: 10 minutes)"""
        expiry_time = self.created_at + timezone.timedelta(minutes=expiry_minutes)
        return timezone.now() > expiry_time
