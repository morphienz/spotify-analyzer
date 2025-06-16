import asyncio
import os
import logging
import time
import functools
from typing import Callable, Any, List, Dict, Optional
from datetime import datetime
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log
)
from pymongo.errors import PyMongoError
from spotipy.exceptions import SpotifyException
from requests.exceptions import RequestException

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
MAX_RETRIES = 5
MIN_WAIT = 2
MAX_WAIT = 30
REQUEST_TIMEOUT = 15

# --- Retry Configurations ---
SPOTIFY_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
    'stop': stop_after_attempt(MAX_RETRIES),
    'retry': retry_if_exception_type(
        (SpotifyException, RequestException, PyMongoError)
    ),
    'before_sleep': before_sleep_log(logger, logging.WARNING),
    'reraise': True
}

MONGO_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=1, max=10),
    'stop': stop_after_attempt(3),
    'retry': retry_if_exception_type(PyMongoError),
    'before_sleep': before_sleep_log(logger, logging.WARNING)
}


# --- Decorators ---
def validate_environment(func: Callable) -> Callable:
    """Gerekli environment değişkenlerini kontrol eden decorator"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        required_vars = [
            'SPOTIPY_CLIENT_ID',
            'SPOTIPY_CLIENT_SECRET',
            'SPOTIPY_REDIRECT_URI',
            'MONGO_URI'
        ]

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise EnvironmentError(
                f"Eksik environment değişkenleri: {', '.join(missing)}"
            )
        return func(*args, **kwargs)

    return wrapper


def timed_execution(func: Callable) -> Callable:
    """Fonksiyon çalışma süresini ölçen decorator"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.monotonic()
        result = func(*args, **kwargs)
        duration = time.monotonic() - start_time
        logger.info(
            f"{func.__name__} fonksiyonu {duration:.2f}s sürdü"
        )
        return result

    return wrapper


# --- Core Functions ---
@retry(**SPOTIFY_RETRY_CONFIG)
def smart_request_with_retry(
        func: Callable,
        *args,
        **kwargs
) -> Any:
    """
    Akıllı yeniden deneme mekanizmalı API isteği
    """
    try:
        return func(*args, **kwargs)
    except SpotifyException as e:
        if e.http_status == 429:
            retry_after = int(e.headers.get('Retry-After', 10))
            logger.warning(
                f"Rate limit aşıldı. {retry_after}s bekleniyor..."
            )
            time.sleep(retry_after)
        raise


@retry(**MONGO_RETRY_CONFIG)
def check_mongo_connection() -> bool:
    """MongoDB bağlantısını test eder"""
    from data_store import check_mongo_connection as _check
    return _check()


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Listeyi belirtilen boyutlarda parçalara ayırır"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def format_error(error: Exception) -> Dict:
    """Hataları API response formatına dönüştürür"""
    return {
        "error_type": error.__class__.__name__,
        "message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }


def validate_track_ids(track_ids: List[str]) -> List[str]:
    """Spotify track ID'lerini valide eder"""
    return [
        tid for tid in track_ids
        if tid and len(tid) == 22 and tid.isalnum()
    ]


def validate_playlist_id(playlist_id: str) -> bool:
    """Playlist ID formatını kontrol eder"""
    return (
            len(playlist_id) == 22
            and playlist_id.isalnum()
    )


# --- Utility Classes ---
class ApiResponseFormatter:
    @staticmethod
    def success(data: dict, status_code: int = 200):
        import logging
        logger = logging.getLogger(__name__)

        logger.debug(f"✔️ success() çağrıldı. Veri tipi: {type(data)}")

        if asyncio.iscoroutine(data):
            logger.error("❌ UYARI: data bir coroutine! await unutulmuş olabilir.")
            raise TypeError("data parametresi bir coroutine. await eksik olabilir.")

        return {
            "status": "success",
            "data": data,
            "status_code": status_code
        }

    @staticmethod
    def error(error: Exception) -> Dict:
        return {
            "status": "error",
            "error": format_error(error),
            "timestamp": datetime.utcnow().isoformat()
        }


class RateLimiter:
    """Rate limit yönetimi için yardımcı sınıf"""

    def __init__(self, calls: int | None = None, period: int | None = None):
        env_calls = int(os.getenv("RATE_LIMIT_CALLS", 20))
        env_period = int(os.getenv("RATE_LIMIT_PERIOD", 10))

        self.calls = calls if calls is not None else env_calls
        self.period = period if period is not None else env_period
        self.timestamps = []

    def __call__(self, func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                now = time.time()
                self.timestamps = [
                    t for t in self.timestamps
                    if now - t < self.period
                ]

                if len(self.timestamps) >= self.calls:
                    sleep_time = self.period - (now - self.timestamps[0])
                    logger.warning(
                        f"Rate limit: {sleep_time:.1f}s bekleniyor..."
                    )
                    await asyncio.sleep(sleep_time)

                self.timestamps.append(time.time())
                return await func(*args, **kwargs)

            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                now = time.time()
                self.timestamps = [
                    t for t in self.timestamps
                    if now - t < self.period
                ]

                if len(self.timestamps) >= self.calls:
                    sleep_time = self.period - (now - self.timestamps[0])
                    logger.warning(
                        f"Rate limit: {sleep_time:.1f}s bekleniyor..."
                    )
                    time.sleep(sleep_time)

                self.timestamps.append(time.time())
                return func(*args, **kwargs)

            return wrapper


# --- Health Checks ---
@validate_environment
@timed_execution
def perform_system_check() -> Dict:
    """Sistem sağlık kontrolü yapar"""
    checks = {
        "spotify_connection": False,
        "mongo_connection": False,
        "environment_variables": False
    }

    try:
        # Environment variables check
        checks["environment_variables"] = all([
            os.getenv('SPOTIPY_CLIENT_ID'),
            os.getenv('SPOTIPY_CLIENT_SECRET'),
            os.getenv('MONGO_URI')
        ])

        # MongoDB connection check
        checks["mongo_connection"] = check_mongo_connection()

        # Spotify connection check
        from spotify_auth import auth_manager
        sp = auth_manager.get_valid_client()
        sp.current_user()
        checks["spotify_connection"] = True

    except Exception as e:
        logger.error(f"Sistem kontrol hatası: {str(e)}")

    return checks