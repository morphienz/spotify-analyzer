# data_store.py
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pymongo import MongoClient, errors, UpdateOne, InsertOne, IndexModel
from pymongo.collection import Collection
from pymongo.database import Database
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from dotenv import load_dotenv
import atexit
from threading import Lock
from bson import ObjectId, errors as bson_errors
from utils import chunk_list, validate_track_ids

# --- Konfigürasyonlar ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Sabitler ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "spotify_analytics"
COLLECTIONS = [
    "track_cache",
    "analyses",
    "auth_tokens",
    "user_tracks",
    "playlist_records",
    "playlists",
    "artist_genres",
    "audit_logs"
]

# --- Yeniden Deneme Konfigürasyonu ---
MONGO_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=2, max=30),
    'stop': stop_after_attempt(5),
    'retry': retry_if_exception_type(errors.PyMongoError),
    'before_sleep': lambda _: logger.warning("MongoDB operasyonu yeniden deneniyor...")
}

# --- MongoDB Manager (Thread-Safe Singleton) ---
class MongoDBManager:
    _instance = None
    _lock = Lock()
    _client: MongoClient = None
    _db: Database = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._connect()
                cls._ensure_indexes()
                cls._ensure_collections()
        return cls._instance

    @classmethod
    @retry(**MONGO_RETRY_CONFIG)
    def _connect(cls):
        """MongoDB bağlantısını kurar ve veritabanını seçer"""
        try:
            cls._client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,
                socketTimeoutMS=10000,
                connectTimeoutMS=10000,
                retryWrites=True,
                appname="SpotifyAnalytics"
            )
            cls._db = cls._client[DB_NAME]
            cls._client.admin.command('ping')
            logger.info("✓ MongoDB bağlantısı başarılı")
        except errors.ConnectionFailure as e:
            logger.critical(f"× MongoDB bağlantı hatası: {str(e)}")
            raise

    @classmethod
    def _ensure_collections(cls):
        """Gerekli koleksiyonları oluşturur"""
        existing = cls._db.list_collection_names()
        for col in COLLECTIONS:
            if col not in existing:
                cls._db.create_collection(col)
                logger.info(f"✓ {col} koleksiyonu oluşturuldu")

    @classmethod
    def _ensure_indexes(cls):
        try:
            cls._db.track_cache.create_indexes([
                IndexModel([("primary_genre", 1), ("last_updated", -1)]),
                IndexModel([("id", 1), ("artist", 1)])
            ])

            existing_indexes = cls._db.analyses.index_information()
            if "created_at_1" not in existing_indexes:
                cls._db.analyses.create_index(
                    "created_at",
                    name="created_at_1",
                    expireAfterSeconds=30 * 86400
                )
            else:
                logger.info("✓ 'created_at_1' indexi zaten var, atlandı.")

            cls._db.auth_tokens.create_index(
                "expires_at",
                expireAfterSeconds=604800
            )

            cls._db.user_tracks.create_index(
                [("user_id", 1), ("track_id", 1)],
                unique=True
            )

            cls._db.playlist_records.create_index(
                [("user_id", 1), ("genre", 1)],
                name="user_genre_index"
            )

            logger.info("✓ MongoDB indexleri güncellendi")
        except Exception as e:
            logger.error(f"Index oluşturma hatası: {str(e)}")

    @classmethod
    def get_collection(cls, collection_name: str) -> Collection:
        if collection_name not in COLLECTIONS:
            raise ValueError(f"Geçersiz koleksiyon: {collection_name}")
        return cls._db[collection_name]

    @classmethod
    def close(cls):
        if cls._client:
            cls._client.close()
            logger.info("✓ MongoDB bağlantısı kapatıldı")


# --- Bağlantı Temizleme ---
atexit.register(MongoDBManager.close)

# --- Çekirdek Fonksiyonlar ---
@retry(**MONGO_RETRY_CONFIG)
def cache_tracks(features: List[Dict]) -> int:
    try:
        if not features:
            return 0

        collection = MongoDBManager().get_collection("track_cache")
        operations = [
            UpdateOne(
                {'_id': f['id']},
                {'$set': {**f, 'last_updated': datetime.utcnow()}},
                upsert=True
            ) for f in features if f.get('id')
        ]

        total_updated = 0
        for batch in chunk_list(operations, 500):
            result = collection.bulk_write(batch, ordered=False)
            total_updated += (result.upserted_count + result.modified_count)

        logger.info(f"✓ {total_updated} track önbelleğe alındı")
        return total_updated
    except errors.BulkWriteError as e:
        logger.error(f"Önbellek güncelleme hatası: {str(e.details)}")
        return 0

@retry(**MONGO_RETRY_CONFIG)
def get_cached_tracks(track_ids: List[str]) -> List[Dict]:
    try:
        validated_ids = validate_track_ids(track_ids)
        collection = MongoDBManager().get_collection("track_cache")
        return list(collection.find({'_id': {'$in': validated_ids}}))
    except errors.PyMongoError as e:
        logger.error(f"Önbellek okuma hatası: {str(e)}")
        return []

@retry(**MONGO_RETRY_CONFIG)
def save_analysis(data: Dict) -> Optional[str]:
    try:
        collection = MongoDBManager().get_collection("analyses")
        audit_collection = MongoDBManager().get_collection("audit_logs")
        data['created_at'] = datetime.utcnow()

        with MongoDBManager()._client.start_session() as session:
            with session.start_transaction():
                result = collection.insert_one(data, session=session)
                audit_collection.insert_one({
                    "action": "analysis_created",
                    "analysis_id": result.inserted_id,
                    "timestamp": datetime.utcnow()
                }, session=session)
                return str(result.inserted_id)
    except errors.PyMongoError as e:
        logger.error(f"Analiz kaydetme hatası: {str(e)}")
        return None

@retry(**MONGO_RETRY_CONFIG)
def load_analysis(analysis_id: str) -> Optional[Dict]:
    try:
        collection = MongoDBManager().get_collection("analyses")
        obj_id = ObjectId(analysis_id)
        result = collection.find_one({'_id': obj_id})
        return result if result else None
    except (bson_errors.InvalidId, TypeError, ValueError) as e:
        logger.error(f"Geçersiz analiz ID: {str(e)}")
        return None
    except errors.PyMongoError as e:
        logger.error(f"Analiz yükleme hatası: {str(e)}")
        return None

@retry(**MONGO_RETRY_CONFIG)
def save_user_tracks(user_id: str, tracks: List[Dict]) -> bool:
    try:
        validated_tracks = [
            {**t, 'track_id': t['id']}
            for t in tracks
            if validate_track_ids([t['id']])
        ]

        collection = MongoDBManager().get_collection("user_tracks")
        operations = [
            UpdateOne(
                {'user_id': user_id, 'track_id': t['track_id']},
                {'$set': {**t, 'last_updated': datetime.utcnow()}},
                upsert=True
            ) for t in validated_tracks
        ]

        collection.bulk_write(operations, ordered=False)
        logger.info(f"✓ {len(validated_tracks)} kullanıcı şarkısı güncellendi")
        return True
    except errors.PyMongoError as e:
        logger.error(f"Kullanıcı verisi kaydetme hatası: {str(e)}")
        return False


@retry(**MONGO_RETRY_CONFIG)
def load_user_tracks(user_id: str) -> List[Dict]:
    """Kullanıcının kaydedilmiş şarkılarını yükler"""
    try:
        collection = MongoDBManager().get_collection("user_tracks")
        cursor = collection.find({"user_id": user_id}, {"_id": 0}).sort("added_at", 1)
        return list(cursor)
    except errors.PyMongoError as e:
        logger.error(f"Kullanıcı verisi yükleme hatası: {str(e)}")
        return []

@retry(**MONGO_RETRY_CONFIG)
def save_playlist_records(playlist_data: Dict) -> bool:
    try:
        collection = MongoDBManager().get_collection("playlist_records")
        playlist_data['created_at'] = datetime.utcnow()

        required_fields = ["user_id", "genre", "track_ids"]
        if not all(field in playlist_data for field in required_fields):
            raise ValueError("Eksik zorunlu alanlar")

        result = collection.insert_one(playlist_data)
        logger.info(f"✓ Playlist kaydı oluşturuldu: {result.inserted_id}")
        return result.acknowledged
    except errors.PyMongoError as e:
        logger.error(f"Playlist kaydetme hatası: {str(e)}")
        return False

@retry(**MONGO_RETRY_CONFIG)
def check_mongo_connection() -> bool:
    try:
        MongoDBManager().get_collection("track_cache").find_one()
        return True
    except errors.PyMongoError as e:
        logger.error(f"MongoDB bağlantı testi başarısız: {str(e)}")
        return False

# --- Yeni Fonksiyon: Kullanıcı Analiz Geçmişi ---
@retry(**MONGO_RETRY_CONFIG)
def get_user_analyses(user_id: str, limit: int = 20) -> List[Dict]:
    """Kullanıcının geçmiş analiz kayıtlarını getirir"""
    try:
        collection = MongoDBManager().get_collection("analyses")
        cursor = collection.find(
            {"user_id": user_id},
            {"_id": 1, "created_at": 1, "tracks": 1, "genres": 1, "playlist_id": 1}
        ).sort("created_at", -1).limit(limit)
        return list(cursor)
    except errors.PyMongoError as e:
        logger.error(f"Kullanıcı analiz geçmişi hatası: {str(e)}")
        return []
