from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import PasswordResetSerializer

from django.contrib.auth import get_user_model
from rest_framework import serializers
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from allauth.account.utils import user_pk_to_url_str
from allauth.account.forms import default_token_generator

from django.core.mail import send_mail
from django.conf import settings

from otp.models import OTPValidation

User = get_user_model()

class CustomRegisterSerializer(RegisterSerializer):
    username = None
    email = serializers.EmailField(required=True)
    profession = serializers.CharField(required=True, max_length=100)
    country = serializers.CharField(required=True, max_length=100)
    city = serializers.CharField(required=True, max_length=100)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('username', None)
        self.fields.pop('phone_number', None)

    @property
    def _has_phone_field(self):
        return False

    def get_cleaned_data(self):
        return {
            "email": self.validated_data.get("email", ""),
            "profession": self.validated_data.get("profession", ""),
            "country": self.validated_data.get("country", ""),
            "city": self.validated_data.get("city", ""),
            "password1": self.validated_data.get("password1", ""),
        }

    def validate_email(self, email):
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("This email is already registered."))
        return email

    def validate_profession(self, profession):
        if not profession or not profession.strip():
            raise serializers.ValidationError(_("Profession is required."))
        return profession.strip()

    def validate_country(self, country):
        if not country or not country.strip():
            raise serializers.ValidationError(_("Country is required."))
        return country.strip()

    def validate_city(self, city):
        if not city or not city.strip():
            raise serializers.ValidationError(_("City is required."))
        return city.strip()

    @transaction.atomic
    def save(self, request):
        adapter = get_adapter()
        self.cleaned_data = self.get_cleaned_data()

        # Step 1: Create the user
        user = adapter.new_user(request)

        # Step 2: Set required fields
        user.email = self.cleaned_data["email"]
        user.profession = self.cleaned_data["profession"]
        user.country = self.cleaned_data["country"]
        user.city = self.cleaned_data["city"]
        user.is_active = False
        user.set_password(self.cleaned_data["password1"])
        user.save()
        setup_user_email(request, user, [])
        adapter.save_user(request, user, self)

        otp = OTPValidation.generate_otp()

        OTPValidation.objects.create(user=user, otp=otp)

        send_mail(
            "Your OTP Code",
            f"Your OTP is: {otp}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        return user



class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'uid',
            'email',
            'first_name',
            'last_name',
            'profession',
            'country',
            'city',
            'profile_image',
            "type",
            'device_token',
            'receive_notifications',
            'is_active_for_receiving',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uid', 'email', 'created_at', 'updated_at']



class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
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
        read_only_fields = ['uid', 'email', 'created_at', 'updated_at']

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['receive_notifications']



class CustomPasswordResetSerializer(PasswordResetSerializer):
    def save(self):
        email = self.validated_data["email"]
        users = User.objects.filter(email__iexact=email, is_active=True)

        for user in users:
            uid = user_pk_to_url_str(user)
            token = default_token_generator.make_token(user)

            reset_path = settings.PASSWORD_RESET_CONFIRM_URL.format(uid=uid, token=token)
            reset_url = f"{settings.FRONTEND_BASE_URL}/{reset_path}"

            subject = "Reset Your Password"
            message = f"Hi,\n\nPlease click the link below to reset your password:\n{reset_url}\n\nIf you did not request this, please ignore this email."

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

