import { useNavigate } from "react-router-dom";

function AnalyzeOptions() {
  const navigate = useNavigate();

  const handleLikedTracks = () => {
    navigate("/analyze/liked");
  };

  const handlePlaylist = () => {
    navigate("/analyze/playlist");
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-black to-gray-900 text-white">
      <h1 className="text-3xl font-bold mb-8 text-green-400">Nasıl analiz etmek istersin?</h1>

      <div className="flex flex-col gap-6">
        <button
          onClick={handleLikedTracks}
          className="bg-green-500 hover:bg-green-600 text-black font-semibold py-3 px-6 rounded-full text-lg transition-all duration-300"
        >
          🎵 Beğenilen Şarkılarımı Analiz Et
        </button>

        <button
          onClick={handlePlaylist}
          className="bg-green-700 hover:bg-green-800 text-white font-semibold py-3 px-6 rounded-full text-lg transition-all duration-300"
        >
          📋 Çalma Listesi Analizi
        </button>
      </div>
    </div>
  );
}

export default AnalyzeOptions;
