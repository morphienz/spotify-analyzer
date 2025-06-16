import os
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from concurrent.futures import ThreadPoolExecutor, as_completed

# Spotify ve Mongo
import spotipy
from spotipy.exceptions import SpotifyException
from pymongo.errors import PyMongoError

# Dahili Modüller
from data_store import (
    save_analysis,
    load_analysis,
    cache_tracks,
    get_cached_tracks,
    save_user_tracks,
    check_mongo_connection,
    MongoDBManager
)
from genre_finder import GenreFinder, get_genre_breakdown
from playlist_creator import PlaylistCreator
from utils import (
    chunk_list,
    validate_track_ids,
    RateLimiter,
    smart_request_with_retry
)
from spotify_auth import auth_manager
from logger import configure_logging
from bson import ObjectId

# --- Konfigürasyon ---
configure_logging()
logger = logging.getLogger(__name__)

# --- Ayarlar ---
MAX_TRACKS = int(os.getenv("MAX_TRACKS", 5000))
DEFAULT_CHUNK_SIZE = 100
REQUEST_DELAY = 0.2
MAX_WORKERS = int(os.getenv("WORKFLOW_MAX_WORKERS", 5))

# --- Retry Ayarları ---
SPOTIFY_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=2, max=30),
    'stop': stop_after_attempt(5),
    'retry': retry_if_exception_type((SpotifyException, PyMongoError)),
    'before_sleep': lambda _: logger.warning("İşlem yeniden deneniyor...")
}


class WorkflowError(Exception):
    def __init__(self, message: str, stage: str):
        self.stage = stage
        super().__init__(f"{stage.upper()} Hatası: {message}")


@retry(**SPOTIFY_RETRY_CONFIG)
def initialize_services() -> Tuple[spotipy.Spotify, Dict]:
    logger.info("🔄 Servisler başlatılıyor...")

    try:
        if not check_mongo_connection():
            raise WorkflowError("MongoDB bağlantısı başarısız", "initialization")

        sp = auth_manager.get_valid_client()
        user = smart_request_with_retry(sp.me)
        logger.info(f"✅ Spotify bağlantısı başarılı: {user['display_name']}")
        return sp, user

    except Exception as e:
        logger.critical(f"❌ Servis başlatma hatası: {str(e)}")
        raise WorkflowError(str(e), "initialization")


@retry(**SPOTIFY_RETRY_CONFIG)
@RateLimiter(calls=5, period=10)
def get_user_tracks(sp: spotipy.Spotify, max_tracks: int = MAX_TRACKS) -> List[Dict]:
    logger.info(f"🎵 En fazla {max_tracks} şarkı yükleniyor...")

    tracks = []
    offset = 0
    retry_count = 0

    try:
        while len(tracks) < max_tracks and retry_count < 3:
            results = smart_request_with_retry(
                sp.current_user_saved_tracks,
                limit=50,
                offset=offset
            )

            batch = [
                {
                    "id": item["track"]["id"],
                    "name": item["track"]["name"],
                    "artist": item["track"]["artists"][0]["name"],
                    "added_at": item["added_at"],
                    "preview_url": item["track"].get("preview_url")
                } for item in results.get("items", []) if item.get("track")
            ]

            if not batch:
                retry_count += 1
                time.sleep(REQUEST_DELAY)
                continue

            tracks.extend(batch)
            offset += len(batch)
            logger.info(f"📥 Yüklenen şarkı: {len(tracks)}/{max_tracks}")
            time.sleep(REQUEST_DELAY)

        return tracks[:max_tracks]

    except Exception as e:
        logger.error(f"Şarkı yükleme hatası: {str(e)}")
        raise WorkflowError(str(e), "track_loading")


def analyze_genres(track_ids: List[str]) -> Dict:
    try:
        logger.info(f"🔍 {len(track_ids)} şarkı için tür analizi başlıyor...")
        finder = GenreFinder()
        genre_map = finder.process_tracks(track_ids)
        logger.info(f"✨ {len(track_ids)} şarkı analiz edildi")
        return genre_map
    except Exception as e:
        logger.error(f"Tür analizi hatası: {str(e)}")
        raise WorkflowError(str(e), "genre_analysis")


@RateLimiter(calls=3, period=60)
async def create_playlists(
        analysis_data: Dict,
        confirmation: bool,
        selected_tracks: Optional[Dict[str, List[str]]] = None,
        excluded_track_ids: Optional[List[str]] = None
) -> Dict:
    try:
        # 1. Gerekli verileri çıkar
        genres = analysis_data.get("genres", {})
        if not genres:
            raise WorkflowError("Analiz verisi eksik veya hatalı", "playlist_creation")

        # 2. Filtreleme işlemleri
        filtered_genres = {}
        if selected_tracks:
            filtered_genres = {
                genre: [tid for tid in track_ids if tid not in (excluded_track_ids or [])]
                for genre, track_ids in selected_tracks.items()
            }
        else:
            filtered_genres = {
                genre: [tid for tid in tids if tid not in (excluded_track_ids or [])]
                for genre, tids in genres.items()
            }

        # 3. Playlist oluşturucuyu başlat
        creator = PlaylistCreator()

        # 4. Playlist oluştur (await ile)
        results = await creator.create_genre_playlists(filtered_genres, confirmation)

        # 5. İstatistikleri hesapla
        stats = {
            "total_playlists": len(results),
            "total_tracks": sum(
                v.get("track_count", 0) for v in results.values() if isinstance(v, dict))
        }

        return {
            "results": results,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Playlist oluşturma hatası: {str(e)}")
        raise WorkflowError(str(e), "playlist_creation")


async def analyze_and_create_playlists(analysis_id: str) -> Dict:
    """Tek fonksiyonla tüm süreci yönet"""
    try:
        analysis = load_analysis(analysis_id)
        if not analysis:
            raise WorkflowError("Analiz bulunamadı", "loading")

        track_ids = [track["id"] for track in analysis.get("tracks", [])]
        genre_map = analyze_genres(track_ids)

        creator = PlaylistCreator()
        results = await creator.create_genre_playlists(genre_map, True)

        return {
            "status": "success",
            "results": results,
            "stats": {
                "total_playlists": len(results),
                "total_tracks": sum(len(tracks) for tracks in results.values())
            }
        }
    except Exception as e:
        logger.error(f"Otomatik süreç hatası: {str(e)}")
        raise

async def run_workflow(
    max_tracks: int = 500,
    confirmation: bool = False,
    enable_caching: bool = True
) -> Dict:
    start_time = time.time()
    result = {
        "status": "started",
        "stats": {},
        "execution_time": 0,
        "error": None,
        "error_stage": None
    }

    try:
        sp, user = initialize_services()
        tracks = get_user_tracks(sp, max_tracks)
        result["stats"]["total_tracks"] = len(tracks)

        if not tracks:
            raise WorkflowError("Kullanıcının kayıtlı şarkısı bulunamadı", "track_loading")

        genre_map = analyze_genres([t["id"] for t in tracks])
        result["stats"]["unique_genres"] = len(genre_map)

        creation_result = await create_playlists(genre_map, confirmation)
        result.update(creation_result)

        analysis_id = save_analysis({
            "tracks": tracks,
            "genres": genre_map,
            "created_at": datetime.utcnow()
        })
        save_user_tracks(user["id"], tracks)

        result.update({
            "status": "completed",
            "analysis_id": analysis_id,
            "execution_time": round(time.time() - start_time, 2)
        })

    except WorkflowError as e:
        result.update({
            "status": "failed",
            "error": str(e),
            "error_stage": e.stage,
            "execution_time": round(time.time() - start_time, 2)
        })

    except Exception as e:
        result.update({
            "status": "error",
            "error": str(e),
            "execution_time": round(time.time() - start_time, 2)
        })

    return result


def print_summary(results: Dict) -> None:
    print("\n" + "=" * 50)
    print(f"{' İŞLEM SONUCU ':=^50}")
    print(f"Durum: {results['status'].upper()}")

    if results["status"] == "completed":
        print(f"\nToplam Şarkı: {results['stats'].get('total_tracks', '-')}")
        print(f"Benzersiz Türler: {results['stats'].get('unique_genres', '-')}")
        print(f"Oluşturulan Playlist: {results['stats'].get('total_playlists', '-')}")
        print(f"Analiz ID: {results.get('analysis_id', '-')}")
        print(f"\nToplam Süre: {results['execution_time']}s")

    elif results["status"] == "failed":
        print(f"\nHATA: {results['error']}")
        print(f"Hata Aşaması: {results['error_stage']}")

    elif results["status"] == "error":
        print(f"\nGENEL HATA: {results['error']}")

    print("=" * 50 + "\n")


# --- Yeni Fonksiyonlar ---

def get_breakdown_for_analysis(analysis_id: str) -> Dict:
    analysis = load_analysis(analysis_id)
    if not analysis or "genres" not in analysis:
        raise WorkflowError("Analiz veya tür verisi bulunamadı", "breakdown")
    return get_genre_breakdown(analysis["genres"])


def get_analysis_details(analysis_id: str) -> List[Dict]:
    analysis = load_analysis(analysis_id)
    if not analysis or "genres" not in analysis:
        raise WorkflowError("Analiz veya tür verisi bulunamadı", "details")

    genre_map = analysis["genres"]
    track_id_set = {tid for tids in genre_map.values() for tid in tids}
    cached_tracks = get_cached_tracks(list(track_id_set))

    track_lookup = {t["_id"]: t for t in cached_tracks}
    for t in analysis.get("tracks", []):
        tid = t.get("id") or t.get("_id")
        if tid:
            track_lookup.setdefault(tid, {}).update({
                "name": t.get("name"),
                "artist": t.get("artist"),
                "preview_url": t.get("preview_url")
            })

    genre_details = {}
    for genre, track_ids in genre_map.items():
        genre_details[genre] = [
            {
                "id": tid,
                "name": track_lookup.get(tid, {}).get("name", "Unknown"),
                "artist": track_lookup.get(tid, {}).get("artist", "Unknown"),
                "preview_url": track_lookup.get(tid, {}).get("preview_url")
            }
            for tid in track_ids if tid in track_lookup
        ]

    return genre_details


def get_filtered_genres(analysis_id: str, excluded_ids: List[str]) -> Dict[str, List[str]]:
    analysis = load_analysis(analysis_id)
    if not analysis or "genres" not in analysis:
        raise WorkflowError("Analiz veya tür verisi bulunamadı", "filter")

    genre_map = analysis["genres"]
    excluded_set = set(excluded_ids)

    return {
        genre: [tid for tid in tids if tid not in excluded_set]
        for genre, tids in genre_map.items()
        if any(tid not in excluded_set for tid in tids)
    }


def get_user_analysis_history(user_id: str) -> List[Dict]:
    db = MongoDBManager()
    collection = db.get_collection("analyses")

    analyses = collection.find(
        {"user_id": user_id},
        {"_id": 1, "created_at": 1, "tracks": 1, "genres": 1, "playlist_id": 1}
    ).sort("created_at", -1)

    return [
        {
            "analysis_id": str(doc["_id"]),
            "created_at": doc.get("created_at"),
            "track_count": len(doc.get("tracks", [])),
            "genre_count": len(doc.get("genres", {}))
        }
        for doc in analyses
    ]


# --- CLI Test ---
if __name__ == "__main__":
    try:
        results = asyncio.run(run_workflow(max_tracks=100, confirmation=True))
        print("\n" + "=" * 50)
        print(f"{' SPOTİFY TÜR ORGANİZATÖRÜ ':=^50}")

        print_summary(results)

    except KeyboardInterrupt:
        print("\n⛔ İşlem kullanıcı tarafından iptal edildi")

    except Exception as e:
        print(f"\n💥 Kritik Hata: {str(e)}")