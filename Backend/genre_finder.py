import os
import logging
import requests
import spotipy
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from dotenv import load_dotenv
from pymongo import UpdateOne
from data_store import MongoDBManager, cache_tracks
from utils import chunk_list, validate_track_ids, RateLimiter

# --- Konfigürasyon ---
load_dotenv()
logger = logging.getLogger(__name__)

# --- Sabitler ---
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
MUSICBRAINZ_USER_AGENT = "Music Data Fetcher (seyyidberatkaraca@gmail.com)"
MAX_WORKERS = int(os.getenv("GENRE_FINDER_MAX_WORKERS", 5))
REQUEST_TIMEOUT = float(os.getenv("GENRE_FINDER_TIMEOUT", 15))
CACHE_TTL_DAYS = int(os.getenv("GENRE_CACHE_TTL", 30))

# --- Retry Ayarları ---
SPOTIFY_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=1, max=5),
    'stop': stop_after_attempt(5),
    'retry': retry_if_exception_type((spotipy.SpotifyException, requests.RequestException)),
    'before_sleep': lambda _: logger.warning("Spotify API hatası, yeniden deneniyor...")
}
EXTERNAL_API_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=1, max=5),
    'stop': stop_after_attempt(3),
    'retry': retry_if_exception_type(requests.RequestException),
    'before_sleep': lambda _: logger.warning("Harici API hatası, yeniden deneniyor...")
}


class GenreFinder:
    def __init__(self):
        self.sp = spotipy.Spotify(auth_manager=self._get_auth_manager())
        self.mongo = MongoDBManager()
        self.rate_limiter = RateLimiter(calls=5, period=1)

    def _get_auth_manager(self):
        return spotipy.oauth2.SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            scope="user-library-read"
        )

    @retry(**SPOTIFY_RETRY_CONFIG)
    def _get_spotify_artist_details(self, artist_id: str) -> Dict:
        collection = self.mongo.get_collection("artist_genres")
        cached = collection.find_one({"_id": artist_id})
        if cached and cached.get("expires_at", datetime.utcnow()) > datetime.utcnow():
            return cached

        artist = self.sp.artist(artist_id)
        genres = artist.get('genres', [])

        update_data = {
            "genres": genres if isinstance(genres, list) else [],
            "expires_at": datetime.utcnow() + timedelta(days=CACHE_TTL_DAYS)
        }
        collection.update_one({"_id": artist_id}, {"$set": update_data}, upsert=True)
        return {**artist, **update_data}

    @retry(**EXTERNAL_API_RETRY_CONFIG)
    @RateLimiter(calls=3, period=10)
    def _get_lastfm_genres(self, artist: str, track: str) -> List[str]:
        try:
            params = {
                "method": "track.getInfo",
                "api_key": LASTFM_API_KEY,
                "artist": artist,
                "track": track,
                "format": "json"
            }
            response = requests.get(
                "http://ws.audioscrobbler.com/2.0/",
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": MUSICBRAINZ_USER_AGENT}
            )
            response.raise_for_status()
            return [tag['name'].lower() for tag in response.json().get('track', {}).get('toptags', {}).get('tag', [])][:5]
        except Exception as e:
            logger.warning(f"Last.fm verisi alınamadı: {e}")
            return []

    @retry(**EXTERNAL_API_RETRY_CONFIG)
    @RateLimiter(calls=2, period=5)
    def _get_musicbrainz_genres(self, artist: str, track: str) -> List[str]:
        try:
            response = requests.get(
                "https://musicbrainz.org/ws/2/recording/",
                params={
                    "query": f'artist:"{artist}" AND recording:"{track}"',
                    "fmt": "json",
                    "limit": 1
                },
                headers={"User-Agent": MUSICBRAINZ_USER_AGENT, "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return [tag['name'].lower() for tag in response.json().get('recordings', [{}])[0].get('tags', [])][:3]
        except Exception as e:
            logger.warning(f"MusicBrainz verisi alınamadı: {e}")
            return []

    def _calculate_genre_weights(self, sources: Dict) -> Dict[str, float]:
        weights = {'spotify': 2.0, 'lastfm': 1.5, 'musicbrainz': 1.2}
        genre_scores = {}
        for source, genres in sources.items():
            for idx, genre in enumerate(genres if isinstance(genres, list) else []):
                score = weights.get(source, 1.0) * (1 - idx / 10)
                genre_scores[genre] = genre_scores.get(genre, 0) + score
        return genre_scores

    def _get_track_genres(self, track_id: str) -> Dict:
        try:
            track = self.sp.track(track_id)
            if not track:
                raise ValueError("track verisi alınamadı")

            artists = track.get("artists", [])
            main_artist = artists[0] if artists else {"name": "unknown", "id": "unknown"}
            artist_name = main_artist.get("name", "unknown")
            track_name = track.get("name", "unknown")

            spotify_genres = self._get_spotify_artist_details(main_artist["id"]).get("genres", [])
            lastfm_genres = self._get_lastfm_genres(artist_name, track_name)
            musicbrainz_genres = self._get_musicbrainz_genres(artist_name, track_name)

            sources = {
                "spotify": spotify_genres if isinstance(spotify_genres, list) else [],
                "lastfm": lastfm_genres if isinstance(lastfm_genres, list) else [],
                "musicbrainz": musicbrainz_genres if isinstance(musicbrainz_genres, list) else [],
            }

            genre_scores = self._calculate_genre_weights(sources)
            genres_list = list(genre_scores.keys())

            if not genres_list:
                return {
                    "track_id": track_id,
                    "genres": [],
                    "primary_genre": "unknown",
                    "confidence": 0.0,
                    "sources": sources,
                    "timestamp": datetime.utcnow()
                }

            primary_genre = max(genre_scores.items(), key=lambda x: x[1], default=(None, 0))

            return {
                "track_id": track_id,
                "genres": genres_list,
                "primary_genre": primary_genre[0],
                "confidence": round(primary_genre[1], 2),
                "sources": sources,
                "timestamp": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Tür analiz hatası ({track_id}): {str(e)}")
            return {"track_id": track_id, "error": str(e)}

    def process_tracks(self, track_ids: List[str]) -> Dict[str, List[str]]:
        validated_ids = validate_track_ids(track_ids)
        genre_map = {}
        cache_batch = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self._get_track_genres, tid): tid for tid in validated_ids}

            for future in as_completed(futures):
                tid = futures[future]
                try:
                    result = future.result()
                    genres = result.get("genres", [])
                    primary = result.get("primary_genre", "unknown") or "unknown"

                    if isinstance(genres, list) and genres:
                        genre_map.setdefault(primary, []).append(tid)

                    cache_batch.append({
                        "id": tid,
                        "genres": genres,
                        "primary_genre": primary,
                        "confidence": result.get("confidence", 0.0),
                        "sources": result.get("sources", {}),
                        "last_updated": datetime.utcnow()
                    })
                except Exception as e:
                    logger.error(f"İşlem hatası ({tid}): {str(e)}")

        if cache_batch:
            for chunk in chunk_list(cache_batch, 500):
                cache_tracks(chunk)

        return genre_map

    def get_genre_analysis(self, playlist_id: str) -> Dict:
        try:
            results = self.sp.playlist_tracks(
                playlist_id,
                fields="items(track(id,name,artists))",
                limit=100
            )
            track_ids = [item['track']['id'] for item in results['items'] if item.get('track')]
            return self.process_tracks(track_ids)
        except Exception as e:
            logger.error(f"Playlist analiz hatası: {str(e)}")
            raise GenreAnalysisError(f"Playlist analizi başarısız: {str(e)}")


class GenreAnalysisError(Exception):
    def __init__(self, message: str):
        super().__init__(f"Tür Analiz Hatası: {message}")


def get_genre_breakdown(genre_map: Dict) -> Dict:
    return {
        genre: {
            "count": len(tracks),
            "percentage": round(len(tracks) / sum(len(v) for v in genre_map.values()) * 100, 2)
        }
        for genre, tracks in genre_map.items()
    }
