import os
import asyncio
import logging
import time
import spotipy
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from spotipy.exceptions import SpotifyException
from pymongo import UpdateOne
from dotenv import load_dotenv

from data_store import MongoDBManager, save_playlist_records
from utils import (
    smart_request_with_retry,
    chunk_list,
    validate_track_ids,
    RateLimiter
)
from spotify_auth import auth_manager
from logger import configure_logging

# --- Konfigürasyon ---
load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)

# --- Sabitler ---
MAX_RETRIES = int(os.getenv("PLAYLIST_MAX_RETRIES", 5))
TRACKS_PER_REQUEST = 90
WAIT_BETWEEN_REQUESTS = float(os.getenv("PLAYLIST_REQUEST_DELAY", 1.2))
PLAYLIST_PREFIX = os.getenv("PLAYLIST_PREFIX", "Analiz - ")
CACHE_TTL_DAYS = int(os.getenv("PLAYLIST_CACHE_TTL", 30))

# --- Retry Ayarları ---
SPOTIFY_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=2, max=30),
    'stop': stop_after_attempt(MAX_RETRIES),
    'retry': retry_if_exception_type(SpotifyException),
    'before_sleep': lambda _: logger.warning("Spotify API hatası, yeniden deneniyor...")
}


class PlaylistCreator:
    def __init__(self):
        self.sp = auth_manager.get_valid_client()
        self.user_id = self._get_current_user_id()
        self.mongo = MongoDBManager()
        self.collection = self.mongo.get_collection("playlists")
        self.rate_limiter = RateLimiter(calls=3, period=10)

    def _get_current_user_id(self) -> str:
        try:
            user = smart_request_with_retry(self.sp.me)
            return user.get("id", "unknown_user")
        except Exception as e:
            logger.error(f"Kullanıcı ID alınamadı: {str(e)}")
            raise PlaylistCreationError("Kullanıcı kimliği alınamadı")

    @retry(**SPOTIFY_RETRY_CONFIG)
    @RateLimiter(calls=2, period=5)
    def _create_playlist(self, name: str, description: str) -> Dict:
        try:
            cached = self.collection.find_one({
                "name": name,
                "owner": self.user_id,
                "expires_at": {"$gt": datetime.utcnow()}
            })

            if cached:
                logger.info(f"🎧 Playlist önbellekten alındı: {name}")
                return cached

            playlist = smart_request_with_retry(
                self.sp.user_playlist_create,
                user=self.user_id,
                name=name,
                public=False,
                description=description
            )

            playlist_doc = {
                "_id": playlist.get("id", ""),
                "name": name,
                "owner": self.user_id,
                "tracks": [],
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=CACHE_TTL_DAYS)
            }

            self.collection.insert_one(playlist_doc)

            try:
                # Follow the playlist so it appears in the user's library
                smart_request_with_retry(
                    self.sp.current_user_follow_playlist, playlist["id"]
                )
            except Exception as e:
                logger.warning(f"Playlist takip edilemedi: {e}")

            return playlist

        except Exception as e:
            logger.error(f"Playlist oluşturulamadı: {str(e)}")
            raise PlaylistCreationError("Yeni playlist oluşturulamadı")

    @retry(**SPOTIFY_RETRY_CONFIG)
    def _add_tracks_safe(self, playlist_id: str, track_ids: List[str]) -> Tuple[bool, int]:
        added_count = 0
        valid_ids = validate_track_ids(track_ids)

        try:
            for chunk in chunk_list(valid_ids, TRACKS_PER_REQUEST):
                smart_request_with_retry(self.sp.playlist_add_items, playlist_id, chunk)

                self.collection.update_one(
                    {"_id": playlist_id},
                    {"$push": {"tracks": {"$each": chunk}}},
                    upsert=True
                )

                added_count += len(chunk)
                time.sleep(WAIT_BETWEEN_REQUESTS)

            return True, added_count

        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 30))
                logger.warning(f"⚠️ Rate limit! {retry_after}s bekleniyor...")
                time.sleep(retry_after)
                return self._add_tracks_safe(playlist_id, track_ids)
            raise

    def _generate_playlist_name(self, genre: str) -> str:
        return genre.title()

    @RateLimiter(calls=1, period=3)
    async def create_genre_playlists(self, genre_map: Dict[str, List[str]], confirmation: bool = False) -> Dict:
        if not confirmation:
            raise PermissionError("Playlist oluşturmak için kullanıcı onayı gereklidir.")

        results = {}

        try:
            for genre, track_ids in genre_map.items():
                if not track_ids or not isinstance(track_ids, list):
                    logger.warning(f"{genre} türü için geçersiz veya boş track listesi.")
                    continue

                filtered_ids = [tid for tid in track_ids if isinstance(tid, str) and tid.strip()]
                if not filtered_ids:
                    logger.warning(f"{genre} türü için geçerli şarkı ID'si bulunamadı.")
                    continue

                try:
                    playlist_name = self._generate_playlist_name(genre)
                    playlist_desc = f"{genre} türündeki parçalar - Otomatik oluşturuldu"

                    # Playlist oluşturma
                    playlist = await asyncio.to_thread(self._create_playlist, playlist_name, playlist_desc)

                    # Şarkı ekleme
                    success, count = await asyncio.to_thread(self._add_tracks_safe, playlist["id"], filtered_ids)

                    results[genre] = {
                        "playlist_id": playlist["id"],
                        "track_count": count,
                        "snapshot_id": playlist.get("snapshot_id", "unknown"),
                        "url": playlist.get("external_urls", {}).get("spotify", "#")
                    }

                    # MongoDB kayıt
                    asyncio.create_task(asyncio.to_thread(save_playlist_records, {
                        "genre": genre,
                        "type": "auto_generated",
                        "user_id": self.user_id,
                        "track_ids": filtered_ids,
                        "created_at": datetime.utcnow()
                    }))

                except Exception as e:
                    logger.error(f"{genre} türü işlenemedi: {str(e)}")
                    results[genre] = {"error": str(e)}

            return results

        except Exception as e:
            logger.critical(f"Toplu playlist oluşturma başarısız: {str(e)}")
            raise PlaylistCreationError("Toplu playlist oluşturulamadı")

    @retry(**SPOTIFY_RETRY_CONFIG)
    def clean_old_playlists(self, days_old: int = 30) -> int:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            to_delete = self.collection.find({
                "owner": self.user_id,
                "created_at": {"$lt": cutoff_date},
                "name": {"$regex": f"^{PLAYLIST_PREFIX}.*"}
            })

            deleted_count = 0

            for playlist in to_delete:
                try:
                    smart_request_with_retry(self.sp.current_user_unfollow_playlist, playlist["_id"])
                    self.collection.delete_one({"_id": playlist["_id"]})
                    deleted_count += 1
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Playlist silme hatası ({playlist['_id']}): {str(e)}")

            logger.info(f"{deleted_count} eski playlist silindi.")
            return deleted_count

        except Exception as e:
            logger.error(f"Eski playlist temizleme hatası: {str(e)}")
            raise PlaylistCleanupError("Eski playlist temizleme başarısız")


class PlaylistCreationError(Exception):
    def __init__(self, message: str):
        super().__init__(f"Playlist Oluşturma Hatası: {message}")


class PlaylistCleanupError(Exception):
    def __init__(self, message: str):
        super().__init__(f"Playlist Temizleme Hatası: {message}")


# --- Test ---
if __name__ == "__main__":
    try:
        creator = PlaylistCreator()
        test_genres = {
            "rock": ["11dFghVXANMlKmJXsNCbNl", "3dRfiJ2650SZu6GbydcHNb"],
            "pop": ["4PTG3Z6ehGkBFwjybzWkR8", "6FED8aeieEnUWwQqAO9zT1"]
        }
        results = creator.create_genre_playlists(test_genres, confirmation=True)
        print("🎶 Oluşturulan Playlist'ler:", results)

        # Temizleme fonksiyonu isteğe bağlı aktif edilebilir
        # print("🧹 Silinen playlist sayısı:", creator.clean_old_playlists(days_old=0))

    except Exception as e:
        print(f"💥 Kritik Hata: {str(e)}")