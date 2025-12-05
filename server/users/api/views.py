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
from users.models import Friendship
from django.db.models import Q
from .serializers import (
    CustomPasswordResetSerializer, 
    NotificationPreferenceSerializer, 
    UserProfileSerializer,
    FriendSerializer,
    FriendshipSerializer
)

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
    """
    Google OAuth authentication endpoint.
    Accepts id_token from Google Sign-In and returns JWT tokens.
    """
    # Accept both 'id_token' (from frontend) and handle the payload
    id_token_str = request.data.get('id_token')
    
    # If id_token is not directly in request.data, check if it's nested
    if not id_token_str:
        # Frontend might send it as part of a nested structure
        if isinstance(request.data, dict) and 'id_token' in request.data:
            id_token_str = request.data['id_token']
        else:
            return Response(
                {'error': 'ID token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    if not id_token_str:
        return Response(
            {'error': 'ID token is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Verify the Google OAuth token
        id_info = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = id_info.get('email')
        if not email:
            return Response(
                {'error': 'Email not found in token.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create user based on email
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': id_info.get('given_name', ''),
                'last_name': id_info.get('family_name', ''),
                'username': email,  # Set username to email for compatibility
            }
        )
        
        # Update user info if it's an existing user (in case Google profile changed)
        if not created:
            if id_info.get('given_name') and not user.first_name:
                user.first_name = id_info.get('given_name', '')
            if id_info.get('family_name') and not user.last_name:
                user.last_name = id_info.get('family_name', '')
            user.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_data': {
                'pk': user.pk,
                'uid': str(user.uid),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': user.display_name,
                'type': user.type,
                'profession': user.profession,
                'country': user.country,
                'city': user.city
            }
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        # Invalid token format or signature
        return Response(
            {'error': f'Invalid Google token: {str(e)}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"Google OAuth error: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {'error': f'Authentication failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




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


class FriendRequestView(APIView):
    """Send a friend request"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if request.user == target_user:
            return Response(
                {"error": "Cannot send friend request to yourself"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if friendship already exists
        existing = Friendship.objects.filter(
            Q(requester=request.user, addressee=target_user) |
            Q(requester=target_user, addressee=request.user)
        ).first()
        
        if existing:
            if existing.status == 'accepted':
                return Response(
                    {"error": "Already friends"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing.requester == request.user:
                return Response(
                    {"error": "Friend request already sent"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                # Other user sent request, auto-accept
                existing.status = 'accepted'
                from django.utils import timezone
                existing.accepted_at = timezone.now()
                existing.save()
                
                # Send notifications
                send_notification(
                    None, request.user, 'friend_request_accepted',
                    description=f"{target_user.display_name} accepted your friend request",
                    send_push=True
                )
                
                return Response({
                    "message": "Friend request accepted",
                    "status": "friends"
                }, status=status.HTTP_200_OK)
        
        # Create new friend request
        friendship = Friendship.objects.create(
            requester=request.user,
            addressee=target_user,
            status='pending'
        )
        
        # Send notification
        send_notification(
            None, target_user, 'friend_request_received',
            description=f"{request.user.display_name} wants to be friends",
            send_push=True
        )
        
        return Response({
            "message": "Friend request sent",
            "status": "pending"
        }, status=status.HTTP_201_CREATED)


class FriendAcceptView(APIView):
    """Accept a friend request"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            requester = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        friendship = Friendship.objects.filter(
            requester=requester,
            addressee=request.user,
            status='pending'
        ).first()
        
        if not friendship:
            return Response(
                {"error": "No pending friend request found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        friendship.status = 'accepted'
        from django.utils import timezone
        friendship.accepted_at = timezone.now()
        friendship.save()
        
        # Send notification
        send_notification(
            None, requester, 'friend_request_accepted',
            description=f"{request.user.display_name} accepted your friend request",
            send_push=True
        )
        
        return Response({
            "message": "Friend request accepted",
            "status": "friends"
        }, status=status.HTTP_200_OK)


class FriendDeclineView(APIView):
    """Decline a friend request"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            requester = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        friendship = Friendship.objects.filter(
            requester=requester,
            addressee=request.user,
            status='pending'
        ).first()
        
        if not friendship:
            return Response(
                {"error": "No pending friend request found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        friendship.delete()
        
        return Response({
            "message": "Friend request declined"
        }, status=status.HTTP_200_OK)


class FriendRemoveView(APIView):
    """Remove a friend or cancel a pending request"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, user_id):
        try:
            target_user = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        friendship = Friendship.objects.filter(
            Q(requester=request.user, addressee=target_user) |
            Q(requester=target_user, addressee=request.user)
        ).first()
        
        if not friendship:
            return Response(
                {"error": "Friendship not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        friendship.delete()
        
        return Response({
            "message": "Friend removed" if friendship.status == 'accepted' else "Friend request cancelled"
        }, status=status.HTTP_200_OK)


class FriendsListView(APIView):
    """Get list of all friends"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        friends = request.user.get_friends()
        serializer = FriendSerializer(friends, many=True, context={'request': request})
        
        return Response({
            "count": len(friends),
            "friends": serializer.data
        }, status=status.HTTP_200_OK)


class FriendStatusView(APIView):
    """Get friendship status with a user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            target_user = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        status_value = request.user.get_friend_status(target_user)
        
        return Response({
            "status": status_value,
            "is_friend": status_value == 'friends'
        }, status=status.HTTP_200_OK)


class PendingFriendRequestsView(APIView):
    """Get pending friend requests (sent and received)"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Received requests
        received = Friendship.objects.filter(
            addressee=request.user,
            status='pending'
        ).select_related('requester')
        
        # Sent requests
        sent = Friendship.objects.filter(
            requester=request.user,
            status='pending'
        ).select_related('addressee')
        
        received_serializer = FriendshipSerializer(received, many=True, context={'request': request})
        sent_serializer = FriendshipSerializer(sent, many=True, context={'request': request})
        
        return Response({
            "received": received_serializer.data,
            "sent": sent_serializer.data,
            "received_count": received.count(),
            "sent_count": sent.count()
        }, status=status.HTTP_200_OK)

