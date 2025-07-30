from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from collections import Counter
from rest_framework.pagination import PageNumberPagination

from music.models import Song, MusicPlatform, SongExchange
from music.match_helpers import (
    find_and_create_automatic_match
)
from .serializers import (
    MatchedSongExchangeSerializer,
    SongSerializer,
    MusicPlatformSerializer,
    SongCreateSerializer
)
from rest_framework.permissions import IsAuthenticated
from music.spotify_utils import get_song_category_from_url


class SongExchangePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    max_page_size_query_param = 'max_page_size'

class MusicPlatformViewSet(viewsets.ModelViewSet):
    """ViewSet for managing music platforms"""
    queryset = MusicPlatform.objects.all()
    serializer_class = MusicPlatformSerializer


class SongViewSet(viewsets.ModelViewSet):
    """ViewSet for managing songs"""
    queryset = Song.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = SongExchangePagination

    def get_serializer_class(self):
        return SongSerializer

    def get_queryset(self):
        return Song.objects.select_related('platform').order_by('-created_at')

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

        spotify_url = request.data.get('url')
        if not spotify_url:
            return Response({'error': 'Spotify URL is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            info = get_song_category_from_url(spotify_url)

            spotify_platform, _ = MusicPlatform.objects.get_or_create(
                name='Spotify',
                defaults={'domain': 'spotify.com'}
            )

            song_data = {
                'title': info['title'],
                'artist': info['artist'],
                'url': spotify_url,
                'spotify_track_id': info['track_id'],
                'album': info['album'],
                'cover_image_url': info['cover_image_url'],
                'platform': spotify_platform.id,
                'duration_seconds': info['duration_seconds'],
                'release_date': info['release_date'],
                'genre': info['genres'],
                'uploader': request.user.id  # Set the uploader
            }

            # Check if song already exists for this user
            existing_song = Song.objects.filter(
                title=info['title'],
                artist=info['artist'],
                platform=spotify_platform,
                uploader=request.user
            ).first()

            if existing_song:
                return Response(
                    {'message': 'You have already added this song', 'song': SongSerializer(existing_song).data},
                    status=status.HTTP_200_OK
                )

            song_serializer = SongCreateSerializer(data=song_data)
            if song_serializer.is_valid():
                song = song_serializer.save()

                matched_song, matched_user = find_and_create_automatic_match(request.user, song)

                response_data = {
                    'message': 'Song imported successfully',
                    'song': SongSerializer(song).data
                }

                if matched_song and matched_user:
                    if matched_user.profile_image and hasattr(matched_user.profile_image, 'url'):
                        profile_image_url = request.build_absolute_uri(matched_user.profile_image.url)
                    else:
                        profile_image_url = None

                    response_data.update({
                        'auto_matched': True,
                        'matched_with': {
                            'song': SongSerializer(matched_song).data,
                            'user': {
                                'id': str(matched_user.id),
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
                    response_data['auto_matched'] = False
                    response_data['message'] += '. No automatic match found, added to matching pool.'

                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(song_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {'error': f'Failed to import song: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class SentSongsMatchedView(generics.ListAPIView):
    serializer_class = MatchedSongExchangeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SongExchangePagination

    def get_queryset(self):
        return SongExchange.objects.filter(
            sender=self.request.user,
            status__in=['matched', 'completed'],
            received_song__isnull=False
        ).select_related('sent_song', 'received_song', 'receiver', 'sent_song__platform', 'received_song__platform').order_by('-created_at')


class GenreDistributionAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        all_genres = []

        for song in Song.objects.only("genre"):
            if isinstance(song.genre, list):
                all_genres.extend(song.genre)
            elif isinstance(song.genre, str):
                all_genres.append(song.genre)

        genre_counts = Counter(all_genres)
        total = sum(genre_counts.values())

        response_data = []

        for genre, count in genre_counts.items():
            percentage = (count / total) * 100
            response_data.append({
                "genre": genre,
                "count": count,
                "percentage": f"{percentage:.0f}%"
            })

        response_data.sort(key=lambda x: float(x["percentage"].strip('%')), reverse=True)

        limit_param = request.query_params.get("limit")
        if limit_param:
            try:
                limit = int(limit_param)
                response_data = response_data[:limit]
            except ValueError:
                pass

        return Response(response_data)
