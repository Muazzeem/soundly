import re
from django.conf import settings

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from collections import Counter
from rest_framework.pagination import PageNumberPagination
from music.models import Song, MusicPlatform, SongExchange
from music.match_helpers import find_and_create_automatic_match
from music.permissions import CanUploadSong
from music.gen_ai import GenFunFact, generate_fun_fact
from .serializers import (
    MatchedSongExchangeSerializer,
    SongSerializer,
    MusicPlatformSerializer,
    SongCreateSerializer,
)
from django.utils import timezone

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
        Create and upload a new song to the platform.

        This endpoint handles two main workflows:
        1. Matched Upload (`matched=true` in request):
           - Validates and saves the uploaded Spotify track.
           - Attempts to automatically match the uploaded song with another user's song using
             `find_and_create_automatic_match()`.
           - If a match is found, both the uploader and the matched user are notified, and the
             response includes details of the matched song and user.
           - If no match is found, the song is added to the matching pool.

        2. Exchange Upload (`matched=false`):
           - Saves the uploaded Spotify track.
           - Creates a `SongExchange` record marking this song as sent by the current user.
           - Selects a **random song** from another user that has never been matched with the current user before.
           - If a random song is found, it marks the exchange as "matched" and assigns the matched song
             to the current exchange record, along with the song's uploader as the receiver.
           - If no song is available, the exchange remains pending.
        """

        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        spotify_url = request.data.get("url")
        matched = str(request.data.get("matched", "")).lower() == "true"

        if not spotify_url:
            return Response({"error": "Spotify URL is required."}, status=status.HTTP_400_BAD_REQUEST)

        pattern = settings.SONG_VALIDATION_PATERN
        if not re.match(pattern, spotify_url):
            return Response({"error": "Invalid Spotify track URL."}, status=status.HTTP_400_BAD_REQUEST)

        info = get_song_category_from_url(spotify_url)

        spotify_platform, _ = MusicPlatform.objects.get_or_create(
            name="Spotify", defaults={"domain": "spotify.com"}
        )

        song = GenFunFact(
            title=info['title'],
            artist=info['artist'],
            url=spotify_url
        )

        fun_fact = generate_fun_fact(song)

        song_data = {
            "title": info["title"],
            "artist": info["artist"],
            "url": spotify_url,
            "spotify_track_id": info["track_id"],
            "album": info["album"],
            "cover_image_url": info["cover_image_url"],
            "platform": spotify_platform.id,
            "duration_seconds": info["duration_seconds"],
            "release_date": info["release_date"],
            "genre": info["genres"],
            "uploader": request.user.id,
            "fun_fact": fun_fact["fact"],
        }

        song_serializer = SongCreateSerializer(data=song_data)
        if not song_serializer.is_valid():
            return Response(song_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        song_instance = song_serializer.save()

        send_notification(None, request.user, "song_uploaded", song_instance,
                          description="Your song was uploaded successfully", send_push=False)

        if matched:
            matched_song, matched_user = find_and_create_automatic_match(request.user, song_instance)
            response_data = {
                "message": "Song imported successfully",
                "song": SongSerializer(song_instance).data,
                "auto_matched": False
            }

            if matched_song and matched_user:
                send_notification(
                    None, matched_user, "song_matched", matched_song,
                    description="Your song was matched with another user's song",
                    send_push=True
                )

                profile_image_url = (
                    request.build_absolute_uri(matched_user.profile_image.url)
                    if matched_user.profile_image and hasattr(matched_user.profile_image, "url")
                    else None
                )

                response_data.update({
                    "auto_matched": True,
                    "matched_with": {
                        "song": SongSerializer(matched_song).data,
                        "user": {
                            "id": str(matched_user.id),
                            "email": matched_user.email,
                            "name": matched_user.first_name,
                            "profile_image_url": profile_image_url,
                            "profession": matched_user.profession or "",
                            "country": matched_user.country or "",
                            "city": matched_user.city or "",
                        },
                    },
                })
            else:
                response_data["message"] += ". No automatic match found, added to matching pool."

            return Response(response_data, status=status.HTTP_201_CREATED)

        else:
            exchange_sender = SongExchange.objects.create(
                sender=request.user,
                sent_song=song_instance,
                status="pending"
            )
            used_song_ids = SongExchange.objects.filter(
                receiver=request.user,
                received_song__isnull=False
            ).values_list("received_song_id", flat=True)

            random_song = (
                Song.objects
                .exclude(uploader=request.user)
                .exclude(id__in=used_song_ids)
                .order_by("?")
                .first()
            )
            if random_song:
                matched_user = random_song.uploader

                exchange_sender.status = "matched"
                exchange_sender.received_song = random_song
                exchange_sender.receiver = request.user
                exchange_sender.matched_at = timezone.now()
                exchange_sender.save()

                SongExchange.objects.create(
                    sender=matched_user,
                    sent_song=random_song,
                    received_song=song_instance,
                    receiver=matched_user,
                    status="matched",
                    matched_at=timezone.now()
                )

                profile_image_url = (
                    request.build_absolute_uri(matched_user.profile_image.url)
                    if matched_user.profile_image and hasattr(matched_user.profile_image, "url")
                    else None
                )

                return Response({
                    "message": "Song imported successfully. Random exchange complete for both users.",
                    "song": SongSerializer(song_instance).data,
                    "matched_with": {
                        "song": SongSerializer(random_song).data,
                        "user": {
                            "id": str(matched_user.id),
                            "email": matched_user.email,
                            "name": matched_user.first_name,
                            "profile_image_url": profile_image_url,
                            "profession": matched_user.profession or "",
                            "country": matched_user.country or "",
                            "city": matched_user.city or "",
                        },
                    },
                }, status=status.HTTP_201_CREATED)

            else:
                return Response({
                    "message": "Song imported successfully. No songs found in exchange pool.",
                    "song": SongSerializer(song_instance).data
                }, status=status.HTTP_201_CREATED)


class SentSongsMatchedView(generics.ListAPIView):
    serializer_class = MatchedSongExchangeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SongExchangePagination

    def get_queryset(self):
        return (
            SongExchange.objects.filter(
                sender=self.request.user,
                status__in=["matched", "completed"],
                received_song__isnull=False,
            )
            .select_related(
                "sent_song",
                "received_song",
                "receiver",
                "sent_song__platform",
                "received_song__platform",
            )
            .order_by("-created_at")
        )


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
            response_data.append(
                {"genre": genre, "count": count, "percentage": f"{percentage:.0f}%"}
            )

        response_data.sort(
            key=lambda x: float(x["percentage"].strip("%")), reverse=True
        )

        limit_param = request.query_params.get("limit")
        if limit_param:
            try:
                limit = int(limit_param)
                response_data = response_data[:limit]
            except ValueError:
                pass

        return Response(response_data)
