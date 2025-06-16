import asyncio
import os
import logging
from bson import ObjectId
from typing import Optional, Dict, List
from datetime import datetime
from fastapi import FastAPI,HTTPException, status, Body, Request, Query,Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt
from fastapi.responses import RedirectResponse
from functools import lru_cache

# Dahili Modüller
from playlist_creator import PlaylistCreator
from spotify_auth import auth_manager
from data_store import (
    cache_tracks,
    get_cached_tracks,
    save_analysis,
    load_analysis,
    save_user_tracks,
    save_playlist_records,
    check_mongo_connection
)
from workflow import (
    create_playlists,
    get_user_tracks,
    analyze_genres,
    get_breakdown_for_analysis,
    get_analysis_details,
    get_filtered_genres,
    get_user_analysis_history
)
from utils import (
    ApiResponseFormatter,
    RateLimiter,
    validate_track_ids,
    chunk_list,
    smart_request_with_retry
)
from logger import configure_logging

# --- Konfigürasyon ---
load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)

# --- CORS Ayarı ---
app = FastAPI(
    title="Spotify Analytics API",
    version="2.3.0",
    description="Spotify kullanıcı analizleri ve playlist yönetimi için gelişmiş API",
    docs_url="/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/analyze-liked")
async def options_analyze_liked():
    return {"message": "OK"}

# --- İstek Modelleri ---
class AnalysisRequest(BaseModel):
    playlist_id: str
    force_refresh: Optional[bool] = False

class PlaylistCreateRequest(BaseModel):
    analysis_id: str
    confirmation: bool
    selected_tracks: Optional[Dict[str, List[str]]] = None
    excluded_track_ids: Optional[List[str]] = None

# --- Retry Ayarları ---
SPOTIFY_RETRY_CONFIG = {
    'wait': wait_exponential(multiplier=1, min=2, max=30),
    'stop': stop_after_attempt(5),
    'reraise': True
}

# --- Yardımcı Fonksiyonlar ---
def get_spotify_client():
    return auth_manager.get_valid_client()

# --- Giriş ve Auth Endpointleri ---
@app.get("/hello")
def test_hello():
    return {"msg": "merhaba aga"}

@app.get("/login", summary="Spotify Login'e Yönlendir")
def login_redirect():
    try:
        auth_url = auth_manager.oauth.get_authorize_url()
        logger.info(f"Spotify authorize URL: {auth_url}")
        return RedirectResponse(auth_url)
    except Exception as e:
        logger.error(f"/login yönlendirme hatası: {str(e)}")
        raise HTTPException(status_code=500, detail="Login yönlendirmesi başarısız.")


@app.get("/start-auth")
def start_auth():
    auth_url = auth_manager.oauth.get_authorize_url()
    return {"auth_url": auth_url}

@app.get("/auth/callback")
def auth_callback(code: str):
    try:
        token_info = auth_manager.oauth.get_access_token(code)  # as_dict kaldırıldı
        token_info = auth_manager._add_metadata(token_info)
        auth_manager._save_token(token_info)

        return RedirectResponse(url=os.getenv("FRONTEND_REDIRECT_URI", "http://127.0.0.1:5173?login=success"))
    except Exception as e:
        logger.error(f"Auth callback hatası: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication failed")

@app.get("/health", summary="Sistem Sağlık Durumu")
async def health_check():
    try:
        health_status = {
            "mongo_connected": check_mongo_connection(),
            "spotify_connected": False,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "version": app.version
        }

        sp = get_spotify_client()
        user = smart_request_with_retry(sp.me)
        health_status["spotify_connected"] = bool(user.get("id"))

        return ApiResponseFormatter.success(health_status)
    except Exception as e:
        return ApiResponseFormatter.error(e)

# --- Analiz Başlat ---
@app.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
@retry(**SPOTIFY_RETRY_CONFIG)
async def analyze_playlist(request: AnalysisRequest = Body(...)):
    logger.info(f"Playlist creation request received: {request.dict()}")
    try:
        sp = get_spotify_client()
        playlist = smart_request_with_retry(
            sp.playlist,
            request.playlist_id,
            fields="name,owner,tracks.total"
        )

        all_track_ids = []
        offset = 0
        total = playlist['tracks']['total']

        while offset < total:
            results = smart_request_with_retry(
                sp.playlist_tracks,
                request.playlist_id,
                limit=100,
                offset=offset,
                fields="items(track(id,name,artists))"
            )
            batch_ids = [
                item['track']['id']
                for item in results['items']
                if item.get('track') and item['track'].get('id')
            ]
            all_track_ids.extend(batch_ids)
            offset += len(results['items'])

        cached_tracks = []
        uncached_ids = all_track_ids
        if not request.force_refresh:
            cached_tracks = get_cached_tracks(all_track_ids)
            cached_ids = [t['_id'] for t in cached_tracks]
            uncached_ids = [tid for tid in all_track_ids if tid not in cached_ids]

        fetched_features = []
        for chunk in chunk_list(uncached_ids, 100):
            response = smart_request_with_retry(sp.audio_features, chunk)
            if response:
                fetched_features += [f for f in response if f]

        cache_tracks(fetched_features)

        analysis_data = {
            "playlist_id": request.playlist_id,
            "playlist_name": playlist['name'],
            "owner": playlist['owner']['display_name'],
            "tracks": {
                "total": total,
                "analyzed": len(cached_tracks) + len(fetched_features)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        analysis_id = save_analysis(analysis_data)

        return ApiResponseFormatter.success(
            {"analysis_id": analysis_id},
            status_code=status.HTTP_202_ACCEPTED
        )

    except Exception as e:
        logger.error(f"Analiz hatası: {str(e)}", exc_info=True)
        return ApiResponseFormatter.error(e)

@app.post("/analyze-liked", status_code=status.HTTP_202_ACCEPTED)
@retry(**SPOTIFY_RETRY_CONFIG)
async def analyze_liked_tracks():
    try:
        sp = get_spotify_client()

        tracks = get_user_tracks(sp, max_tracks=50)
        if not tracks:
            raise HTTPException(status_code=404, detail="Beğenilen şarkı bulunamadı.")

        track_ids = [t["id"] for t in tracks]
        genre_map = analyze_genres(track_ids)

        user_id = smart_request_with_retry(sp.me)["id"]
        analysis_id = save_analysis({
            "source": "liked_tracks",
            "user_id": user_id,
            "tracks": tracks,
            "genres": genre_map,
            "created_at": datetime.utcnow()
        })

        save_user_tracks(user_id, tracks)

        return ApiResponseFormatter.success({"analysis_id": analysis_id})

    except Exception as e:
        logger.error(f"Beğenilen şarkı analizi hatası: {str(e)}", exc_info=True)
        return ApiResponseFormatter.error(e)

# --- Playlist Oluşturma ---
@app.post("/playlists/full-auto")
async def full_auto_playlist_creation(analysis_id: str = Body(..., embed=True)):
    try:
        # 1. Analiz verisini yükle
        analysis = load_analysis(analysis_id)
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analiz bulunamadı"
            )

        # 2. Tür verisi hazır mı kontrol et
        if analysis.get("genres"):
            genre_map = analysis["genres"]
        else:
            # Önceden analiz edilmemişse şarkıları alıp analiz et
            track_ids = [track["id"] for track in analysis.get("tracks", [])]
            genre_map = analyze_genres(track_ids)

        # 4. Playlist oluştur
        creator = PlaylistCreator()
        results = await creator.create_genre_playlists(genre_map, confirmation=True)

        # 5. Sonuçları döndür
        return {
            "status": "success",
            "created_playlists": len(results),
            "total_tracks": sum(len(tracks) for tracks in results.values())
        }

    except Exception as e:
        logger.error(f"Otomatik playlist oluşturma hatası: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/playlists", summary="Playlist Oluştur", status_code=status.HTTP_201_CREATED)
@RateLimiter(calls=3, period=60)
async def create_playlists_endpoint(request: PlaylistCreateRequest = Body(...)):
    try:
        if not request.confirmation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Kullanıcı onayı gereklidir"
            )

        analysis = load_analysis(request.analysis_id)
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Geçersiz analiz ID"
            )

        result = await create_playlists(
            analysis_data=analysis,
            confirmation=True,
            selected_tracks=request.selected_tracks,
            excluded_track_ids=request.excluded_track_ids or []
        )

        return ApiResponseFormatter.success({
            "created_playlists": len(result.get("results", {})),
            "total_tracks": result.get("stats", {}).get("total_tracks", 0)
        })

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Playlist oluşturma hatası: {str(e)}", exc_info=True)
        return ApiResponseFormatter.error(e)

# --- Analiz Sonuçları ve Ek Veriler ---
@app.get("/analysis/{analysis_id}")
async def get_analysis_results(analysis_id: str):
    try:
        analysis = load_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analiz bulunamadı")

        if "_id" in analysis and isinstance(analysis["_id"], ObjectId):
            analysis["_id"] = str(analysis["_id"])

        return ApiResponseFormatter.success(analysis)

    except Exception as e:
        return ApiResponseFormatter.error(e)

@app.get("/analysis/{analysis_id}/breakdown")
async def get_analysis_breakdown(analysis_id: str):
    try:
        breakdown = get_breakdown_for_analysis(analysis_id)
        return ApiResponseFormatter.success(breakdown)
    except Exception as e:
        return ApiResponseFormatter.error(e)

@app.get("/analysis/{analysis_id}/details")
async def get_analysis_details_endpoint(analysis_id: str):
    try:
        details = get_analysis_details(analysis_id)
        return ApiResponseFormatter.success(details)
    except Exception as e:
        return ApiResponseFormatter.error(e)

@app.get("/analysis/{analysis_id}/filtered")
async def get_filtered_analysis(analysis_id: str, exclude: List[str] = Query(default=[])):
    try:
        filtered = get_filtered_genres(analysis_id, exclude)
        return ApiResponseFormatter.success(filtered)
    except Exception as e:
        return ApiResponseFormatter.error(e)

@app.get("/user/analyses")
async def list_user_analyses():
    try:
        user_id = get_spotify_client().me()["id"]
        history = get_user_analysis_history(user_id)
        return ApiResponseFormatter.success(history)
    except Exception as e:
        return ApiResponseFormatter.error(e)

@app.get("/progress/{analysis_id}")
async def get_analysis_progress(analysis_id: str):
    try:
        # Şimdilik dummy: analiz yapıldıktan sonra %100 tamamlandı varsayımı
        return ApiResponseFormatter.success({
            "analysis_id": analysis_id,
            "status": "completed",
            "progress": 100
        })
    except Exception as e:
        return ApiResponseFormatter.error(e)

# --- Uygulama Başlatıcısı ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8080)),
        reload=os.getenv("DEBUG_MODE", "false").lower() == "true"
    )