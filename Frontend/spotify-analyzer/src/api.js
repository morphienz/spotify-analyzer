export const createPlaylists = async (analysisId, selectedTracks = {}, excludedTracks = []) => {
  try {
    const response = await fetch("http://127.0.0.1:8080/playlists", {
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

export const fetchUserProfile = async () => {
  const response = await fetch(`${import.meta.env.VITE_API_URL}/user/profile`, {
    credentials: "include",
    mode: "cors",
  });
  const data = await response.json();
  if (!response.ok || data.status === "error") {
    throw new Error(data.error?.message || "Profil alınamadı.");
  }
  return data.data;
};

export const logout = async () => {
  const response = await fetch(`${import.meta.env.VITE_API_URL}/logout`, {
    method: "POST",
    credentials: "include",
    mode: "cors",
  });
  const data = await response.json();
  if (!response.ok || data.status === "error") {
    throw new Error(data.error?.message || "Çıkış yapılamadı.");
  }
  return data.data;
};

