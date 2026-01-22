import logging
from google.auth.transport import requests
from google.oauth2 import id_token
from rest_framework.views import APIView

logger = logging.getLogger(__name__)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from dj_rest_auth.views import PasswordResetView
from dj_rest_auth.registration.views import RegisterView

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework import generics
from music.models import Song
from users.choices import UserTypeChoice
from users.models import Friendship
from django.db.models import Q
from core.decorators import handle_api_errors, validate_uuid
from .serializers import (
    CustomPasswordResetSerializer, 
    NotificationPreferenceSerializer, 
    UserProfileSerializer,
    UserSerializer,
    FriendSerializer,
    FriendshipSerializer
)

from core.notification import send_notification

User = get_user_model()
GOOGLE_CLIENT_ID = "360088028570-suabtj6mk43m9vdp1n5cdn443i1rr9i0.apps.googleusercontent.com"

class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated]

    @handle_api_errors
    def delete(self, request):
        user = request.user
        user_email = user.email
        user.delete()
        logger.info(f"User {user_email} deleted their account")
        return Response({"detail": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



class UserProfileView(generics.RetrieveUpdateAPIView):
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


class PublicUserProfileView(generics.RetrieveAPIView):
    """View to get another user's public profile"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uid'
    lookup_url_kwarg = 'user_id'

    def get_queryset(self):
        return User.objects.all()



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
@handle_api_errors
def google_auth(request):
    """
    Google OAuth authentication endpoint.
    Accepts id_token from Google Sign-In and returns JWT tokens.
    """
    # Input validation
    id_token_str = request.data.get('id_token', '').strip()
    
    if not id_token_str:
        logger.warning("Google auth attempted without id_token")
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
        logger.error(f"Google OAuth error: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Authentication failed. Please try again.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




class CustomPasswordResetView(PasswordResetView):
    serializer_class = CustomPasswordResetSerializer


class CustomRegisterView(RegisterView):
    """Custom registration view with error logging"""
    
    def post(self, request, *args, **kwargs):
        logger.info(f"Registration attempt for email: {request.data.get('email', 'unknown')}")
        logger.debug(f"Registration data keys: {list(request.data.keys())}")
        
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 201:
                logger.info(f"Registration successful for: {request.data.get('email')}")
            else:
                logger.warning(f"Registration failed with status {response.status_code} for {request.data.get('email', 'unknown')}")
                logger.warning(f"Error details: {response.data}")
            return response
        except Exception as e:
            logger.error(f"Registration exception for {request.data.get('email', 'unknown')}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Registration failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@handle_api_errors
def check_daily_upload_limit(request):
    try:
        user = request.user

        if user.type == UserTypeChoice.BASIC:
            temp_song = Song(uploader=user)
            remaining_uploads = temp_song.remaining_uploads

            return Response({
                "remaining_uploads": remaining_uploads
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "response": "Unlimited uploads"
            }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error checking upload limit for {request.user.email}: {str(e)}", exc_info=True)
        return Response(
            {"error": "Failed to check upload limit"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class FriendRequestView(APIView):
    """Send a friend request"""
    permission_classes = [IsAuthenticated]
    
    @handle_api_errors
    @validate_uuid('user_id')
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            logger.warning(f"User {request.user.email} attempted to send friend request to non-existent user {user_id}")
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}", exc_info=True)
            return Response(
                {"error": "Invalid user ID"},
                status=status.HTTP_400_BAD_REQUEST
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
                
                # Send notification to requester
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
        
        # Send notification to recipient
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
    
    @handle_api_errors
    @validate_uuid('user_id')
    def post(self, request, user_id):
        try:
            requester = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            logger.warning(f"User {request.user.email} attempted to accept friend request from non-existent user {user_id}")
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}", exc_info=True)
            return Response(
                {"error": "Invalid user ID"},
                status=status.HTTP_400_BAD_REQUEST
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
        
        # Send notification to requester
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
    
    @handle_api_errors
    @validate_uuid('user_id')
    def post(self, request, user_id):
        try:
            requester = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            logger.warning(f"User {request.user.email} attempted to decline friend request from non-existent user {user_id}")
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}", exc_info=True)
            return Response(
                {"error": "Invalid user ID"},
                status=status.HTTP_400_BAD_REQUEST
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
    
    @handle_api_errors
    @validate_uuid('user_id')
    def delete(self, request, user_id):
        try:
            target_user = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            logger.warning(f"User {request.user.email} attempted to remove non-existent user {user_id}")
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}", exc_info=True)
            return Response(
                {"error": "Invalid user ID"},
                status=status.HTTP_400_BAD_REQUEST
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
    
    @handle_api_errors
    def get(self, request):
        try:
            friends = request.user.get_friends()
            serializer = FriendSerializer(friends, many=True, context={'request': request})
            
            return Response({
                "count": len(friends),
                "friends": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching friends for {request.user.email}: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to fetch friends"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FriendStatusView(APIView):
    """Get friendship status with a user"""
    permission_classes = [IsAuthenticated]
    
    @handle_api_errors
    @validate_uuid('user_id')
    def get(self, request, user_id):
        try:
            target_user = User.objects.get(uid=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}", exc_info=True)
            return Response(
                {"error": "Invalid user ID"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        status_value = request.user.get_friend_status(target_user)
        
        return Response({
            "status": status_value,
            "is_friend": status_value == 'friends'
        }, status=status.HTTP_200_OK)


class PendingFriendRequestsView(APIView):
    """Get pending friend requests (sent and received)"""
    permission_classes = [IsAuthenticated]
    
    @handle_api_errors
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


class UserSearchView(APIView):
    """Search for users by name or email"""
    permission_classes = [IsAuthenticated]
    
    @handle_api_errors
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        # Input validation
        if not query:
            return Response({
                "error": "Search query is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(query) < 2:
            logger.warning(f"Search query too short ({len(query)} chars) from {request.user.email}")
            return Response({
                "error": "Search query must be at least 2 characters"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(query) > 100:
            logger.warning(f"Search query too long ({len(query)} chars) from {request.user.email}")
            return Response({
                "error": "Search query must be less than 100 characters"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Search by name (first_name, last_name) or email
        # Exclude current user
        users = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).exclude(
            id=request.user.id
        ).select_related().order_by('first_name', 'last_name')[:50]  # Limit to 50 results
        
        # Get friendship status for each user
        results = []
        for user in users:
            friend_status = request.user.get_friend_status(user)
            
            profile_image_url = None
            if user.profile_image:
                try:
                    profile_image_url = request.build_absolute_uri(user.profile_image.url)
                except:
                    pass
            
            results.append({
                'uid': str(user.uid),
                'email': user.email,
                'name': user.display_name,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profession': user.profession,
                'country': user.country,
                'city': user.city,
                'profile_image_url': profile_image_url,
                'friend_status': friend_status,
                'is_friend': friend_status == 'friends',
            })
        
        return Response({
            "count": len(results),
            "users": results
        }, status=status.HTTP_200_OK)
