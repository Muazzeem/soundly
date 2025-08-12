from google.auth.transport import requests
from google.oauth2 import id_token
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from dj_rest_auth.views import PasswordResetView

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework import generics
from music.models import Song
from users.choices import UserTypeChoice
from .serializers import CustomPasswordResetSerializer, NotificationPreferenceSerializer, UserProfileSerializer

from core.notification import send_notification

User = get_user_model()
GOOGLE_CLIENT_ID = "360088028570-suabtj6mk43m9vdp1n5cdn443i1rr9i0.apps.googleusercontent.com"

class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"detail": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



class UserProfileView(generics.RetrieveUpdateAPIView):
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        send_notification(None, request.user, "user_profile_updated", description="Your profile was updated successfully")
        return self.partial_update(request, *args, **kwargs)

    def get_object(self):
        return self.request.user



class NotificationToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        serializer = NotificationPreferenceSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Notification preference updated.",
                "receive_notifications": serializer.data['receive_notifications']
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def google_auth(request):
    id_token_str = request.data.get('id_token')

    if not id_token_str:
        return Response(
            {'error': 'ID token is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = id_info.get('email')
        if not email:
            return Response({'error': 'Email not found in token.'}, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': id_info.get('given_name', ''),
                'last_name': id_info.get('family_name', ''),
            }
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_data': {
                'pk': user.pk,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'type': user.type,
                'profession': user.profession,
                'country': user.country,
                'city': user.city
            }
        }, status=status.HTTP_200_OK)

    except ValueError:
        return Response({'error': 'Invalid Google token'}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class CustomPasswordResetView(PasswordResetView):
    serializer_class = CustomPasswordResetSerializer


@api_view(['GET'])
def check_daily_upload_limit(request):
    user = request.user

    if not user or not user.is_authenticated:
        return Response(
            {"error": "Not authenticated"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if user.type == UserTypeChoice.BASIC:
        temp_song = Song(uploader=user)
        remaining_uploads = temp_song.remaining_uploads

        return Response({
            "remaining_uploads": remaining_uploads
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "response": "Unlimited uploads"
        },
        status=status.HTTP_200_OK)

