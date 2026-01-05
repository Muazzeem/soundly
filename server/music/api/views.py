import re
import logging
from django.conf import settings

from rest_framework import viewsets, status

logger = logging.getLogger(__name__)
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from collections import Counter
from rest_framework.pagination import PageNumberPagination
from music.models import Song, MusicPlatform, SongExchange
from music.match_helpers import find_and_create_automatic_match, find_and_create_random_match
from music.permissions import CanUploadSong
from music.gen_ai import GenFunFact, generate_fun_fact
from core.decorators import handle_api_errors, validate_uuid
from .serializers import (
    MatchedSongExchangeSerializer,
    SongSerializer,
    MusicPlatformSerializer,
    SongCreateSerializer,
)

from rest_framework.permissions import IsAuthenticated
from music.spotify_utils import get_song_category_from_url

from core.notification import send_notification


class SongExchangePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    max_page_size_query_param = "max_page_size"


class MusicPlatformViewSet(viewsets.ModelViewSet):
    """ViewSet for managing music platforms"""

    queryset = MusicPlatform.objects.all()
    serializer_class = MusicPlatformSerializer


class SongViewSet(viewsets.ModelViewSet):
    """ViewSet for managing songs"""

    queryset = Song.objects.all()
    permission_classes = [IsAuthenticated, CanUploadSong]
    pagination_class = SongExchangePagination

    def get_serializer_class(self):
        return SongSerializer

    def get_queryset(self):
        return Song.objects.select_related("platform").order_by("-created_at")

    def create(self, request, *args, **kwargs):
        """
        Create a new song from Spotify URL
        """
        try:
            if not request.user.is_authenticated:
                return Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

            spotify_url = request.data.get('url')
            genre_match = str(request.data.get('genre_match', 'false')).lower()
            logger.info(f"Song upload request - URL: {spotify_url}, genre_match: {genre_match}, user: {request.user.email}")
            logger.debug(f"Request data: {request.data}")

            if not spotify_url:
                logger.warning(f"Song upload failed: Missing URL for user {request.user.email}")
                return Response({'error': 'Spotify URL is required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                info = get_song_category_from_url(spotify_url)
                if not info:
                    logger.warning(f"Failed to fetch song info - URL: {spotify_url}")
                    return Response({
                        'error': 'Invalid Spotify URL or unable to fetch song information. Please check the URL and try again.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except ValueError as e:
                # Spotify credentials missing
                logger.error(f"Spotify credentials error: {str(e)}")
                return Response({
                    'error': 'Spotify API is not configured. Please contact support.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                logger.error(f"Error fetching song info from Spotify URL: {str(e)}", exc_info=True)
                error_msg = str(e)
                if '401' in error_msg or 'Unauthorized' in error_msg:
                    return Response({
                        'error': 'Spotify API authentication failed. Please check API credentials.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response({
                    'error': f'Failed to fetch song information: {error_msg}'
                }, status=status.HTTP_400_BAD_REQUEST)

            spotify_platform, _ = MusicPlatform.objects.get_or_create(
                name='Spotify',
                defaults={'domain': 'spotify.com'}
            )

            # Generate fun fact with error handling
            fun_fact_text = ""
            try:
                song = GenFunFact(
                    title=info.get('title', 'Unknown Title'),
                    artist=info.get('artists', 'Unknown Artist'),
                    url=spotify_url
                )
                logger.info(f"Generating fun fact for song: {song.title} by {song.artist}")
                fun_fact = generate_fun_fact(song)
                fun_fact_text = fun_fact.get('fact', '') if isinstance(fun_fact, dict) else str(fun_fact)
                if fun_fact_text:
                    logger.info(f"Successfully generated fun fact for '{song.title}': {fun_fact_text[:50]}...")
                else:
                    logger.warning(f"Fun fact generation returned empty result for '{song.title}'")
            except ValueError as e:
                # API key not configured
                logger.error(f"GOOGLE_API_KEY not configured: {str(e)}")
                fun_fact_text = ""
            except Exception as e:
                logger.error(f"Failed to generate fun fact for song '{info.get('title', 'Unknown')}': {str(e)}", exc_info=True)
                # Continue without fun fact - it's not critical
                fun_fact_text = ""

            # Safely extract info with defaults
            song_data = {
                'title': info.get('title', 'Unknown Title'),
                'artist': info.get('artists', 'Unknown Artist'),
                'url': spotify_url,
                'spotify_track_id': info.get('track_id', ''),
                'album': info.get('album', ''),
                'cover_image_url': info.get('cover_image_url', ''),
                'platform': spotify_platform.id,
                'duration_seconds': info.get('duration_seconds'),
                'release_date': info.get('release_date', ''),
                'genre': info.get('genres', []) if info.get('genres') and len(info.get('genres', [])) > 0 else ["unknown"],
                'uploader': request.user.id,
                'fun_fact': fun_fact_text
            }

            song_serializer = SongCreateSerializer(data=song_data)
            if song_serializer.is_valid():
                try:
                    song = song_serializer.save()
                except Exception as e:
                    logger.error(f"Error saving song: {str(e)}", exc_info=True)
                    return Response({
                        'error': 'Failed to save song. Please try again.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Initialize variables
                matched_song = None
                matched_user = None
                match_type = None

                try:
                    if genre_match == 'true':
                        matched_song, matched_user = find_and_create_automatic_match(request.user, song)
                        match_type = 'automatic'

                    elif genre_match == 'false':
                        matched_song, matched_user = find_and_create_random_match(request.user, song)
                        match_type = 'random'
                except Exception as e:
                    logger.error(f"Error during song matching: {str(e)}", exc_info=True)
                    # Continue without match - song is still saved
                    matched_song = None
                    matched_user = None
                    match_type = None

                try:
                    song_serialized = SongSerializer(song, context={'request': request}).data
                except Exception as e:
                    logger.error(f"Error serializing song: {str(e)}", exc_info=True)
                    # Fallback to basic song data
                    song_serialized = {
                        'uid': str(song.uid),
                        'title': song.title,
                        'artist': song.artist,
                        'url': song.url,
                    }
                
                response_data = {
                    'message': 'Song imported successfully',
                    'song': song_serialized
                }

                if not info.get('genres') or len(info.get('genres', [])) == 0 and genre_match == 'true':
                    response_data['message'] += '.This song does not have a genre set by the artist. It will be exchanged in the Random Match pool'

                if matched_song and matched_user:
                    # Generate fun fact for received song if it doesn't have one
                    if not matched_song.fun_fact or not matched_song.fun_fact.strip():
                        try:
                            logger.info(f"Generating fun fact for received song: {matched_song.title} by {matched_song.artist}")
                            received_song_fun_fact = GenFunFact(
                                title=matched_song.title,
                                artist=matched_song.artist,
                                url=matched_song.url
                            )
                            fun_fact_result = generate_fun_fact(received_song_fun_fact)
                            fun_fact_text = fun_fact_result.get('fact', '') if isinstance(fun_fact_result, dict) else str(fun_fact_result)
                            
                            if fun_fact_text and fun_fact_text.strip():
                                matched_song.fun_fact = fun_fact_text.strip()
                                matched_song.save(update_fields=['fun_fact'])
                                logger.info(f"Successfully generated and saved fun fact for received song '{matched_song.title}'")
                            else:
                                logger.warning(f"Fun fact generation returned empty result for received song '{matched_song.title}'")
                        except ValueError as e:
                            # API key not configured
                            logger.error(f"GOOGLE_API_KEY not configured, cannot generate fun fact for received song: {str(e)}")
                        except Exception as e:
                            logger.error(f"Failed to generate fun fact for received song '{matched_song.title}': {str(e)}", exc_info=True)
                            # Continue without fun fact - it's not critical
                    
                    # Only send notifications for genre matches (not random matches)
                    if match_type == 'automatic':
                        try:
                            send_notification(
                                None, request.user, 'song_matched', matched_song,
                                description=f'Your song was matched with another user\'s song.',
                                send_push=True, target_url=matched_song.url if matched_song else None
                            )

                            send_notification(
                                None, matched_user, 'song_matched', matched_song,
                                description=f'Your song was matched with another user\'s song.',
                                send_push=True, target_url=matched_song.url if matched_song else None
                            )
                        except Exception as e:
                            logger.warning(f"Failed to send match notifications: {str(e)}")

                    # Get profile image URL
                    if matched_user.profile_image and hasattr(matched_user.profile_image, 'url'):
                        profile_image_url = request.build_absolute_uri(matched_user.profile_image.url)
                    else:
                        profile_image_url = None

                    # Serialize matched song (refresh from DB to get updated fun_fact)
                    matched_song.refresh_from_db()
                    try:
                        matched_song_data = SongSerializer(matched_song, context={'request': request}).data
                    except Exception as e:
                        logger.warning(f"Error serializing matched song: {str(e)}")
                        matched_song_data = {
                            'uid': str(matched_song.uid),
                            'title': matched_song.title,
                            'artist': matched_song.artist,
                            'url': matched_song.url,
                            'fun_fact': getattr(matched_song, 'fun_fact', '') or '',
                        }
                    
                    # Update response based on match type
                    response_data.update({
                        'matched_with': {
                            'song': matched_song_data,
                            'user': {
                                'id': str(matched_user.id),
                                'uid': str(matched_user.uid),
                                'email': matched_user.email,
                                'name': matched_user.first_name,
                                'profile_image_url': profile_image_url,
                                'profession': matched_user.profession or "",
                                'country': matched_user.country or "",
                                'city': matched_user.city or "",
                            }
                        }
                    })
                else:
                    if genre_match:
                        response_data['message'] += '. No songs available for genre match, added to matching pool.'
                    else:
                        response_data['message'] += '. No songs available for random match, added to matching pool.'
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                logger.warning(f"Song serializer validation failed: {song_serializer.errors}")
                return Response({
                    'error': 'Invalid song data.',
                    'details': song_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error in song creation: {str(e)}", exc_info=True)
            return Response({
                'error': 'An unexpected error occurred while uploading the song. Please try again.',
                'details': str(e) if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SentSongsMatchedView(generics.ListAPIView):
    serializer_class = MatchedSongExchangeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SongExchangePagination

    def get_queryset(self):
        # Check if user_uid is provided in query params
        user_uid = self.request.query_params.get('user_uid')
        
        if user_uid:
            try:
                from users.models import User
                target_user = User.objects.get(uid=user_uid)
                sender_user = target_user
            except User.DoesNotExist:
                return SongExchange.objects.none()
        else:
            sender_user = self.request.user
        
        return (
            SongExchange.objects.filter(
                sender=sender_user,
                status__in=["matched", "completed"],
                received_song__isnull=False,
            )
            .select_related(
                "sent_song",
                "received_song",
                "sender",
                "receiver",
                "sent_song__platform",
                "received_song__platform",
                "sent_song__uploader",
                "received_song__uploader",
            )
            .order_by("-created_at")
        )
    
    def get_serializer_context(self):
        """Pass request context to serializer for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ReceivedSongsMatchedView(generics.ListAPIView):
    """View for songs received by the current user"""
    serializer_class = MatchedSongExchangeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SongExchangePagination

    def get_queryset(self):
        return (
            SongExchange.objects.filter(
                receiver=self.request.user,
                status__in=["matched", "completed"],
                received_song__isnull=False,
            )
            .select_related(
                "sent_song",
                "received_song",
                "sender",
                "sent_song__platform",
                "received_song__platform",
                "received_song__uploader",
            )
            .order_by("-created_at")
        )
    
    def get_serializer_context(self):
        """Pass request context to serializer for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class UserReceivedSongsView(generics.ListAPIView):
    """View for songs received by a specific user (by UID)"""
    serializer_class = MatchedSongExchangeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SongExchangePagination
    lookup_field = 'uid'
    lookup_url_kwarg = 'user_uid'

    def get_queryset(self):
        user_uid = self.kwargs.get('user_uid')
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            target_user = User.objects.get(uid=user_uid)
        except User.DoesNotExist:
            return SongExchange.objects.none()
        
        return (
            SongExchange.objects.filter(
                receiver=target_user,
                status__in=["matched", "completed"],
                received_song__isnull=False,
            )
            .select_related(
                "sent_song",
                "received_song",
                "sender",
                "sent_song__platform",
                "received_song__platform",
                "received_song__uploader",
            )
            .order_by("-created_at")
        )
    
    def get_serializer_context(self):
        """Pass request context to serializer for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class GenreDistributionAPIView(APIView):
    permission_classes = [AllowAny]

    @handle_api_errors
    def get(self, request):
        try:
            all_genres = []

            for song in Song.objects.only("genre"):
                if isinstance(song.genre, list):
                    all_genres.extend(song.genre)
                elif isinstance(song.genre, str):
                    all_genres.append(song.genre)

            genre_counts = Counter(all_genres)
            total = sum(genre_counts.values())

            if total == 0:
                return Response([])

            response_data = []

            for genre, count in genre_counts.items():
                percentage = (count / total) * 100
                response_data.append(
                    {"genre": genre, "count": count, "percentage": f"{percentage:.0f}%"}
                )

            response_data.sort(
                key=lambda x: float(x["percentage"].strip("%")), reverse=True
            )

            # Input validation for limit parameter
            limit_param = request.query_params.get("limit")
            if limit_param:
                try:
                    limit = int(limit_param)
                    if limit < 1 or limit > 100:
                        logger.warning(f"Invalid limit parameter: {limit}")
                        limit = 50  # Default to 50 if invalid
                    response_data = response_data[:limit]
                except ValueError:
                    logger.warning(f"Invalid limit parameter format: {limit_param}")
                    pass

            return Response(response_data)
        except Exception as e:
            logger.error(f"Error in genre distribution: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to fetch genre distribution"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
