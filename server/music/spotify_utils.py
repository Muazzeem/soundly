import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
from django.conf import settings

logger = logging.getLogger(__name__)

def get_spotify_client():
    """Get authenticated Spotify client"""
    client_id = settings.SPOTIPY_CLIENT_ID
    client_secret = settings.SPOTIPY_CLIENT_SECRET
    
    if not client_id or not client_secret:
        logger.error("Spotify API credentials (SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET) are not configured")
        raise ValueError("Spotify API credentials are not configured. Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET in your .env file.")
    
    client_credentials_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_song_category_from_url(song_url):
    """Enhanced function to get song details from Spotify URL"""
    try:
        match = re.search(r'track/([a-zA-Z0-9]+)', song_url)
        if not match:
            return None

        track_id = match.group(1)
        sp = get_spotify_client()

        # Get track details
        track = sp.track(track_id)

        song_title = track['name']
        album_name = track['album']['name']
        duration_ms = track['duration_ms']
        release_date = track['album']['release_date']

        cover_image_url = ''
        if track['album']['images']:
            cover_image_url = track['album']['images'][0]['url']

        all_genres = set()
        artist_names = []
        for artist in track['artists']:
            artist_names.append(artist['name'])
            artist_data = sp.artist(artist['uri'])
            all_genres.update(artist_data.get('genres', []))

        artist_names_str = ", ".join(artist_names)
        logger.debug(f"Retrieved artist names: {artist_names_str}")

        return {
            'title': song_title,
            'artists': artist_names_str,
            'album': album_name,
            'duration_seconds': duration_ms // 1000 if duration_ms else None,
            'track_id': track_id,
            'genres': list(all_genres),
            'cover_image_url': cover_image_url,
            'release_date': release_date
        }

    except Exception as e:
        logger.error(f"Error fetching song details from Spotify: {e}", exc_info=True)
        return None
