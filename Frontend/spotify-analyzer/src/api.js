import { API_BASE_URL } from "./config.js";

export const createPlaylists = async (analysisId, selectedTracks = {}, excludedTracks = []) => {
  try {
    const response = await fetch(`${API_BASE_URL}/playlists`, {
      method: "POST",
      mode: "cors",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        analysis_id: analysisId,
        confirmation: true,
        selected_tracks: selectedTracks,
        excluded_track_ids: excludedTracks,
      }),
    });

    const data = await response.json();
    if (!response.ok || data.status === "error") {
      throw new Error(data.detail || "Playlist oluşturulamadı.");
    }

    return data;
  } catch (err) {
    console.error("🎯 API playlist error:", err);
    throw err;
  }
};

export const fetchUserAnalyses = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/user/analyses`, {
      method: "GET",
      mode: "cors",
      credentials: "include",
    });

    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.detail || data.message || "Analiz geçmişi alınamadı.");
    }

    return data.data;
  } catch (err) {
    console.error("🎯 API history error:", err);
    throw err;
  }
};

export const fetchUserProfile = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/user/profile`, {
      method: "GET",
      mode: "cors",
      credentials: "include",
    });

    const data = await response.json();

    if (!response.ok || data.status !== "success") {
      throw new Error(data.detail || data.message || "Profil alınamadı.");
    }

    const profile = data.data || {};
    if (profile.display_name) {
      localStorage.setItem("userName", profile.display_name);
    }
    if (profile.images && profile.images[0]?.url) {
      localStorage.setItem("userImage", profile.images[0].url);
    }
    // Store full profile for persistence
    localStorage.setItem("profile", JSON.stringify(profile));

    return profile;
  } catch (err) {
    console.error("🎯 API profile error:", err);
    throw err;
  }
};

export const logout = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/logout`, {
      method: "POST",
      mode: "cors",
      credentials: "include",
    });

    const data = await response.json();

    if (!response.ok || data.status !== "success") {
      throw new Error(data.detail || data.message || "Çıkış başarısız.");
    }

    return data;
  } catch (err) {
    console.error("🎯 API logout error:", err);
    throw err;
  }
};

export const fetchAuthUrl = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/start-auth`, {
      method: "GET",
      mode: "cors",
      credentials: "include",
    });

    const data = await response.json();

    if (!response.ok || !data.auth_url) {
      throw new Error(data.detail || "Yetkilendirme adresi alınamadı.");
    }

    return data.auth_url;
  } catch (err) {
    console.error("🎯 API auth url error:", err);
    throw err;
  }
};

