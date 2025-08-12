import spotipy

from spotipy.oauth2 import SpotifyClientCredentials
import re
from django.conf import settings

def get_spotify_client():
    """Get authenticated Spotify client"""
    client_credentials_manager = SpotifyClientCredentials(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET
    )
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_song_category_from_url(song_url):
    """Enhanced function to get song details from Spotify URL"""
    try:
        match = re.search(r'track/([a-zA-Z0-9]+)', song_url)
        if not match:
            return None, None, []

        track_id = match.group(1)
        sp = get_spotify_client()

        # Get track details
        track = sp.track(track_id)

        song_title = track['name']
        artist_name = track['artists'][0]['name']
        album_name = track['album']['name']
        duration_ms = track['duration_ms']
        release_date = track['album']['release_date']


        cover_image_url = ''
        if track['album']['images']:
            cover_image_url = track['album']['images'][0]['url']

        # Get artist genres
        artist_uri = track['artists'][0]['uri']
        artist = sp.artist(artist_uri)
        genres = artist['genres']

        return {
            'title': song_title,
            'artist': artist_name,
            'album': album_name,
            'duration_seconds': duration_ms // 1000 if duration_ms else None,
            'track_id': track_id,
            'genres': genres,
            'cover_image_url': cover_image_url,
            'release_date': release_date
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

