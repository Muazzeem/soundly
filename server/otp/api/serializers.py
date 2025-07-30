# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.core.mail import send_mail
from django.conf import settings

from otp.models import OTPValidation

User = get_user_model()


class OTPValidationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, max_length=15)
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")
        otp = attrs.get("otp")

        if not email and not phone:
            raise serializers.ValidationError("Either email or phone must be provided")

        try:
            if email:
                user = User.objects.get(email=email)
            else:
                user = User.objects.get(phone=phone)

            otp_obj = OTPValidation.objects.get(user=user)

            if otp_obj.is_verified:
                raise serializers.ValidationError("OTP already verified")

            if otp_obj.is_expired():
                raise serializers.ValidationError("OTP expired")

            if otp_obj.otp != otp:
                raise serializers.ValidationError("Invalid OTP")

            attrs["user"] = user
            attrs["otp_obj"] = otp_obj
            return attrs

        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        except OTPValidation.DoesNotExist:
            raise serializers.ValidationError("OTP validation record not found")


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get("email")

        try:
            user = User.objects.get(email=email)
            if user.is_active:
                raise serializers.ValidationError("User is already verified")

            attrs["user"] = user
            return attrs

        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
