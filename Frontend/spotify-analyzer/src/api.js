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

export const fetchUserAnalyses = async () => {
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/user/analyses`, {
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

