from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from otp.models import OTPValidation
from .serializers import OTPValidationSerializer, ResendOTPSerializer
from core.notification import send_notification


class VerifyOTPView(APIView):
    """Verify OTP for user registration"""

    def post(self, request):
        serializer = OTPValidationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            otp_obj = serializer.validated_data["otp_obj"]

            user.is_active = True
            user.save()

            otp_obj.is_verified = True
            otp_obj.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "pk": user.pk,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name
                    }
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendOTPView(APIView):
    """Resend OTP for registration verification"""

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Generate new OTP
            try:
                otp_obj = OTPValidation.objects.get(user=user)
                otp_obj.otp = OTPValidation.generate_otp()
                otp_obj.is_verified = False
                otp_obj.created_at = timezone.now()
                otp_obj.save()
            except OTPValidation.DoesNotExist:
                otp_obj = OTPValidation.objects.create(
                    user=user, otp=OTPValidation.generate_otp()
                )

            # Send OTP via email if available
            if user.email:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Resending OTP to {user.email}: {otp_obj.otp}")
                
                try:
                    send_mail(
                        "Your New Registration OTP",
                        f"Your new OTP for account verification is: {otp_obj.otp}",
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    logger.info(f"OTP email sent to {user.email}")
                except Exception as e:
                    logger.error(f"Failed to send OTP email to {user.email}: {str(e)}", exc_info=True)

            # If you have SMS functionality, add it here
            # For example:
            # if user.phone:
            #     send_sms(user.phone, f'Your OTP for verification is: {otp_obj.otp}')

            return Response(
                {"detail": "New OTP sent to your email/phone."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
