import os
import logging
from datetime import datetime
from typing import Optional, Dict
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
TOKEN_COLLECTION = "auth_tokens"
TOKEN_EXPIRY_BUFFER = 300  # 5 minutes buffer
MAX_RETRIES = 5

# --- Retry Configuration ---
MONGO_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=2, max=30),
    'stop': stop_after_attempt(MAX_RETRIES),
    'retry': retry_if_exception_type(PyMongoError),
    'before_sleep': lambda _: logger.warning("MongoDB işlemi yeniden deneniyor...")
}


class TokenManager:
    def __init__(self):
        load_dotenv()
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("MONGO_DB", "spotify_analytics")]
        self.collection = self.db[TOKEN_COLLECTION]

    @retry(**MONGO_RETRY_CONFIG)
    def validate_token(self, token_data: Dict) -> bool:
        """Token'ın geçerliliğini kontrol eder"""
        if not token_data:
            return False

        expiry_time = token_data.get('expires_at', 0)
        return datetime.now().timestamp() < (expiry_time - TOKEN_EXPIRY_BUFFER)

    @retry(**MONGO_RETRY_CONFIG)
    def read_token(self, user_id: str = "system") -> Optional[Dict]:
        """MongoDB'den token'ı okur"""
        try:
            return self.collection.find_one({"_id": user_id})
        except PyMongoError as e:
            logger.error(f"Token okuma hatası: {str(e)}")
            return None

    @retry(**MONGO_RETRY_CONFIG)
    def write_token(self, token_data: Dict, user_id: str = "system") -> bool:
        """Token'ı MongoDB'ye kaydeder"""
        try:
            token_data['_id'] = user_id
            token_data['last_updated'] = datetime.utcnow()

            result = self.collection.replace_one(
                {"_id": user_id},
                token_data,
                upsert=True
            )

            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Token yazma hatası: {str(e)}")
            return False

    @retry(**MONGO_RETRY_CONFIG)
    def delete_token(self, user_id: str = "system") -> bool:
        """Token'ı MongoDB'den siler"""
        try:
            result = self.collection.delete_one({"_id": user_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Token silme hatası: {str(e)}")
            return False

    @retry(**MONGO_RETRY_CONFIG)
    def rotate_tokens(self) -> bool:
        """Süresi dolan token'ları temizler"""
        try:
            result = self.collection.delete_many({
                "expires_at": {"$lt": datetime.now().timestamp()}
            })
            logger.info(f"{result.deleted_count} süresi dolmuş token silindi")
            return True
        except PyMongoError as e:
            logger.error(f"Token rotasyon hatası: {str(e)}")
            return False


# Global token manager instance'ı
token_manager = TokenManager()