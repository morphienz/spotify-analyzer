import os
import logging
from datetime import datetime
from typing import Optional, Dict
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

from data_store import MongoDBManager

# --- .env Yüklemesi ---
load_dotenv()

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if not os.getenv("SPOTIPY_CLIENT_ID") or not os.getenv("SPOTIPY_CLIENT_SECRET"):
    logger.error("Spotify client bilgileri eksik. .env dosyasını kontrol edin.")

# --- Constants ---
SCOPES = "playlist-modify-private playlist-modify-public user-library-read user-top-read"
TOKEN_COLLECTION = "auth_tokens"
TOKEN_EXPIRY_BUFFER = 300  # 5 minutes

# --- Retry Configuration ---
RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=2, max=30),
    'stop': stop_after_attempt(5),
    'retry': retry_if_exception_type((PyMongoError, spotipy.SpotifyException)),
    'before_sleep': lambda _: logger.warning("Auth hatası, yeniden deneniyor...")
}


class SpotifyAuthManager:
    def __init__(self):
        self.oauth = SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            scope=SCOPES,
            cache_path=None  # MongoDB kullanıldığı için devre dışı
        )
        self.mongo = MongoDBManager()
        self.current_user: Optional[str] = None

        def set_current_user(self, user_id: str | None):
            """Geçerli kullanıcıyı ayarla"""
            self.current_user = user_id

    @retry(**RETRY_CONFIG)
    def get_valid_client(self) -> spotipy.Spotify:
        """Geçerli bir Spotify client instance'ı döndürür"""
        token_info = self._load_token()

        if not token_info or self._is_token_expired(token_info):
            token_info = self._refresh_token(token_info)

        if not token_info:
            raise spotipy.SpotifyException("Authentication failed", -1)

        return spotipy.Spotify(auth=token_info['access_token'])

    @retry(**RETRY_CONFIG)
    def _load_token(self) -> Optional[Dict]:
        """Token'ı MongoDB'den yükler"""
        if not self.current_user:
            return None
        collection = self.mongo.get_collection(TOKEN_COLLECTION)
        return collection.find_one({"_id": self.current_user})

    @retry(**RETRY_CONFIG)
    def _save_token(self, token_info: Dict, user_id: Optional[str] = None) -> None:
        """Token'ı MongoDB'ye kaydeder"""
        collection = self.mongo.get_collection(TOKEN_COLLECTION)
        uid = user_id or self.current_user
        if not uid:
            raise ValueError("User ID bilinmiyor")
        token_info['_id'] = uid
        collection.replace_one({"_id": uid}, token_info, upsert=True)
        logger.info("Token MongoDB'ye kaydedildi")

    def _is_token_expired(self, token_info: Dict) -> bool:
        """Token süresi dolmuş mu kontrol eder"""
        return datetime.now().timestamp() > token_info['expires_at'] - TOKEN_EXPIRY_BUFFER

    @retry(**RETRY_CONFIG)
    def _refresh_token(self, old_token: Optional[Dict]) -> Optional[Dict]:
        """Yalnızca refresh_token ile token yeniler"""
        if old_token and 'refresh_token' in old_token:
            try:
                new_token = self.oauth.refresh_access_token(old_token['refresh_token'])
                new_token = self._add_metadata(new_token)
                self._save_token(new_token)
                logger.info("Token başarıyla yenilendi")
                return new_token
            except Exception as e:
                logger.error(f"Token yenileme hatası: {str(e)}")
                return None
        return None

    def _add_metadata(self, token_info: Dict) -> Dict:
        """Token'a ek metadata ekler"""
        token_info['expires_at'] = int(token_info['expires_in']) + int(datetime.now().timestamp())
        return token_info

    def clear_tokens(self, user_id: Optional[str] = None) -> bool:
        """Belirtilen kullanıcının token'ını temizler"""
        try:
            collection = self.mongo.get_collection(TOKEN_COLLECTION)
            uid = user_id or self.current_user
            query = {"_id": uid} if uid else {}
            result = collection.delete_many(query)
            logger.info(f"{result.deleted_count} token silindi")
            return True
        except PyMongoError as e:
            logger.error(f"Token temizleme hatası: {str(e)}")
            return False


# Global auth manager instance
auth_manager = SpotifyAuthManager()
