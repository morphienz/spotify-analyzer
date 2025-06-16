import { useState } from "react";
import { useNavigate } from "react-router-dom";
import UserMenu from "../components/UserMenu.jsx";
import PageWrapper from "../components/PageWrapper.jsx";
import { API_BASE_URL } from "../config.js";

function AnalyzePlaylist() {
  const [playlistUrl, setPlaylistUrl] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const extractId = (url) => {
    const match = url.match(/playlist\/(.+?)(\?|$)/);
    return match ? match[1] : url;
  };

  const handleAnalyze = async () => {
    const playlistId = extractId(playlistUrl.trim());
    if (!playlistId) return;
    setLoading(true);
    setStatus("Analiz başlatılıyor...");
    try {
      const res = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ playlist_id: playlistId }),
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setStatus("Analiz tamamlandı, yönlendiriliyor...");
        setTimeout(() => navigate(`/result/${data.data.analysis_id}`), 1000);
      } else {
        throw new Error(data.message || "Analiz başarısız");
      }
    } catch (e) {
      setStatus(`Hata: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper>
      <div className="flex flex-col items-center justify-center h-screen bg-black text-white gap-4 relative">
        <UserMenu />
        <h1 className="text-2xl font-bold mb-4">Çalma Listesi Analizi</h1>
        <input
          type="text"
          value={playlistUrl}
          onChange={(e) => setPlaylistUrl(e.target.value)}
          placeholder="Playlist URL veya ID"
          className="w-80 px-3 py-2 rounded text-black"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading || !playlistUrl.trim()}
          className="bg-green-500 hover:bg-green-600 text-black font-semibold py-2 px-6 rounded-full disabled:bg-gray-600"
        >
          Analiz Et
        </button>
        {status && <p className="mt-4 text-center">{status}</p>}
      </div>
    </PageWrapper>
  );
}

export default AnalyzePlaylist;

