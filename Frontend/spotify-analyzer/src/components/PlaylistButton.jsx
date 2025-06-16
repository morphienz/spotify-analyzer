import { useState } from "react";
import { API_BASE_URL } from "../config.js";

function PlaylistButton({
  analysisId,
  genres,
  selectedGenres,
  excludedTrackIds
}) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);

  const handleCreatePlaylist = async () => {
    setLoading(true);
    setSuccess(null);

    const selectedTracks = {};
    for (const genre of selectedGenres) {
      if (genres[genre]) {
        selectedTracks[genre] = genres[genre]
          .map((track) => track.id)
          .filter((id) => !excludedTrackIds.includes(id));
      }
    }

    const body = {
      analysis_id: analysisId,
      confirmation: true,
      selected_tracks: selectedTracks,
      excluded_track_ids: excludedTrackIds
    };

    try {
      const res = await fetch(`${API_BASE_URL}/playlists`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      const data = await res.json();
      if (data.status === "success") {
        setSuccess(`🎉 ${data.data.created_playlists} playlist oluşturuldu!`);
      } else {
        setSuccess("❌ Playlist oluşturulamadı.");
      }
    } catch (e) {
      console.error(e);
      setSuccess("❌ Sunucu hatası.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-12 text-center">
      <button
        onClick={handleCreatePlaylist}
        disabled={loading || selectedGenres.size === 0}
        className={`px-6 py-3 rounded-full font-bold text-lg transition duration-300 ease-in-out ${
          loading
            ? "bg-gray-700 cursor-not-allowed"
            : "bg-green-500 hover:bg-green-600 text-black"
        }`}
      >
        {loading ? "Oluşturuluyor..." : "Playlist Oluştur"}
      </button>
      {success && <div className="mt-4 text-green-300 font-medium">{success}</div>}
    </div>
  );
}

export default PlaylistButton;
