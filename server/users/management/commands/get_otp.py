"""
Django management command to get the current OTP for a user.
Usage: python manage.py get_otp <email>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from otp.models import OTPValidation

User = get_user_model()


class Command(BaseCommand):
    help = 'Get the current OTP for a user by email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email address')

    def handle(self, *args, **options):
        email = options['email']

        try:
            user = User.objects.get(email=email)
            
            try:
                otp_obj = OTPValidation.objects.get(user=user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nOTP for {email}: {otp_obj.otp}\n'
                        f'Created: {otp_obj.created_at}\n'
                        f'Verified: {otp_obj.is_verified}\n'
                        f'Expired: {otp_obj.is_expired()}\n'
                    )
                )
            except OTPValidation.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'No OTP found for user: {email}')
                )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {email} does not exist')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
