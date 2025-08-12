from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from music.models import Song, SongExchange
from core.notification import send_notification


def get_song_with_platform(uid):
    return get_object_or_404(Song.objects.select_related('platform'), uid=uid)


def normalize_genres(genres):
    if not genres:
        return []
    return [g.lower().strip() for g in genres if g.strip()]


def get_potential_matches(original_song, genre_list):
    genre_query = Q()
    for genre in genre_list:
        genre_query |= Q(genre__icontains=genre)

    qs = Song.objects.filter(genre_query).exclude(uid=original_song.uid)

    if hasattr(original_song, 'uploader') and original_song.uploader:
        qs = qs.exclude(uploader=original_song.uploader)

    return qs.select_related('platform').distinct()


def find_and_create_automatic_match(current_user, new_song):
    """
    Find an automatic match for a new song and create bidirectional exchanges
    Returns: (matched_song, matched_user) or (None, None) if no match found
    """
    genre_list = normalize_genres(new_song.genre)

    if not genre_list:
        return None, None

    pending_exchanges = SongExchange.objects.filter(
        status='pending',
        received_song__isnull=True,
        receiver__isnull=True
    ).exclude(sender=current_user).select_related('sent_song', 'sender')

    compatible_exchanges = []
    for exchange in pending_exchanges:
        exchange_genres = normalize_genres(exchange.sent_song.genre)
        overlapping_genres = set(genre_list) & set(exchange_genres)

        if overlapping_genres:
            match_score = len(overlapping_genres)
            total_unique = len(set(genre_list) | set(exchange_genres))
            similarity = (match_score / total_unique) * 100 if total_unique else 0

            compatible_exchanges.append({
                'exchange': exchange,
                'similarity': similarity,
                'overlapping_genres': list(overlapping_genres)
            })

    if not compatible_exchanges:
        SongExchange.objects.create(
            sender=current_user,
            sent_song=new_song,
            status='pending'
        )
        return None, None

    compatible_exchanges.sort(key=lambda x: x['similarity'], reverse=True)
    best_match = compatible_exchanges[0]

    original_exchange = best_match['exchange']
    matched_song = original_exchange.sent_song
    matched_user = original_exchange.sender

    original_exchange.receiver = current_user
    original_exchange.received_song = new_song
    original_exchange.status = 'matched'
    original_exchange.matched_at = timezone.now()
    original_exchange.save()

    reciprocal_exchange = SongExchange.objects.create(
        sender=current_user,
        receiver=matched_user,
        sent_song=new_song,
        received_song=matched_song,
        status='matched',
        matched_at=timezone.now()
    )

    return matched_song, matched_user


def find_and_create_random_match(current_user, new_song):
    """
    Find a random song match and create exchanges.
    Returns: (matched_song, matched_user) or (None, None) if no songs available
    """
    available_songs = Song.objects.exclude(
        uploader=current_user
    ).select_related('platform', 'uploader')

    songs_list = list(available_songs)

    if not songs_list:
        SongExchange.objects.create(
            sender=current_user,
            sent_song=new_song,
            status='pending'
        )
        return None, None

    matched_song = random.choice(songs_list)
    matched_user = matched_song.uploader

    # Create the original exchange
    SongExchange.objects.create(
        sender=current_user,
        receiver=matched_user,
        sent_song=new_song,
        received_song=matched_song,
        status='matched',
        matched_at=timezone.now()
    )

    # Create the reciprocal exchange
    SongExchange.objects.create(
        sender=matched_user,
        receiver=current_user,
        sent_song=matched_song,
        received_song=new_song,
        status='matched',
        matched_at=timezone.now()
    )

    return matched_song, matched_user


def process_matches(user, original_song, genre_list, potential_matches):
    results = []
    seen = set()

    for match in potential_matches:
        match_genres = normalize_genres(match.genre)
        overlapping = list(set(genre_list) & set(match_genres))
        if not overlapping:
            continue

        key = (match.title, match.artist)
        if key in seen:
            continue
        seen.add(key)

        match_score = len(overlapping)
        total_unique = len(set(genre_list) | set(match_genres))
        similarity = (match_score / total_unique) * 100 if total_unique else 0

        exchange = SongExchange.objects.filter(
            sender=user,
            sent_song=original_song,
            received_song=match
        ).first()

        if not exchange:
            exchange = SongExchange.objects.create(
                sender=user,
                sent_song=original_song,
                received_song=match,
                status='pending'
            )

        results.append(serialize_match(match, overlapping, match_score, similarity, exchange))

    results.sort(key=lambda x: (x['match_info']['match_score'], x['match_info']['similarity_percentage']), reverse=True)
    return results


def serialize_match(match, overlapping_genres, score, similarity, exchange):
    return {
        'uid': str(match.uid),
        'title': match.title,
        'artist': match.artist,
        'album': match.album,
        'genre': match.genre,
        'url': match.url,
        'duration_seconds': match.duration_seconds,
        'release_date': match.release_date,
        'cover_image_url': match.cover_image_url,
        'platform': {
            'id': match.platform.id,
            'name': match.platform.name
        } if match.platform else None,
        'match_info': {
            'overlapping_genres': overlapping_genres,
            'match_score': score,
            'similarity_percentage': round(similarity, 2)
        },
        'exchange_status': exchange.status,
        'uploader_info': {
            'id': str(match.uploader.id),
            'email': match.uploader.email
        } if hasattr(match, 'uploader') and match.uploader else None
    }


def serialize_random_match(match, exchange):
    """
    Serialize a random match without genre-based matching info
    """
    return {
        'uid': str(match.uid),
        'title': match.title,
        'artist': match.artist,
        'album': match.album,
        'genre': match.genre,
        'url': match.url,
        'duration_seconds': match.duration_seconds,
        'release_date': match.release_date,
        'cover_image_url': match.cover_image_url,
        'platform': {
            'id': match.platform.id,
            'name': match.platform.name
        } if match.platform else None,
        'match_info': {
            'match_type': 'random',
            'overlapping_genres': [],
            'match_score': 0,
            'similarity_percentage': 0
        },
        'exchange_status': exchange.status,
        'uploader_info': {
            'id': str(match.uploader.id),
            'email': match.uploader.email
        } if hasattr(match, 'uploader') and match.uploader else None
    }


def serialize_original_song(song):
    return {
        'uid': str(song.uid),
        'title': song.title,
        'artist': song.artist,
        'genre': song.genre
    }
