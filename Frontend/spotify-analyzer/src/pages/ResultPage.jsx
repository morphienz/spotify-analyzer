import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import UserMenu from "../components/UserMenu.jsx";
import PageWrapper from "../components/PageWrapper.jsx";
import { Pie } from "react-chartjs-2";
import "chart.js/auto";
import SelectionPanel from "../components/SelectionPanel";
import { API_BASE_URL } from "../config.js";

function ResultPage() {
  const { analysisId } = useParams();
  const [genres, setGenres] = useState([]);
  const [selectedGenres, setSelectedGenres] = useState([]);
  const [genreTrackMap, setGenreTrackMap] = useState({});
  const [excludedTrackIds, setExcludedTrackIds] = useState([]);
  const [manualAssignments, setManualAssignments] = useState({});
  const [analysisStats, setAnalysisStats] = useState({
    totalTracks: 0,
    genreCount: 0,
    unknownCount: 0,
  });
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchBreakdown = async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/analysis/${analysisId}/breakdown`,
        );
        const { data, status, message } = await res.json();
        if (status === "success") {
          const genreList = Object.entries(data).map(([genre, value]) => ({
            genre,
            percentage: value.percentage,
            count: value.count,
          }));
          setGenres(genreList);
        } else {
          throw new Error(message || "Tür verisi alınamadı.");
        }
      } catch (err) {
        console.error("❌ Breakdown fetch error:", err);
        setError("Tür yüzdesi alınamadı.");
      } finally {
        setLoading(false);
      }
    };

    fetchBreakdown();
  }, [analysisId]);

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/analysis/${analysisId}/details`,
        );
        const { data, status } = await res.json();
        if (status === "success") {
          setGenreTrackMap(data.tracks);
          const allGenres = data.tracks || {};
          const totalTracks = Object.values(allGenres).reduce(
            (sum, arr) => sum + arr.length,
            0,
          );
          const genreCount = Object.keys(allGenres).length;
          const unknownCount = (allGenres["unknown"] || []).length;
          setAnalysisStats({ totalTracks, genreCount, unknownCount });
        }
      } catch (err) {
        console.error("❌ Details fetch error:", err);
      }
    };

    fetchDetails();
  }, [analysisId]);

  const toggleGenreSelection = (genre) => {
    setSelectedGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre],
    );
  };
  const getCountForGenre = (genre) =>
    genres.find((g) => g.genre === genre)?.count || 0;

  const getCountForGenre = (genre) =>
    genres.find((g) => g.genre === genre)?.count || 0;

  const toggleExclude = (id) => {
    setExcludedTrackIds((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id],
    );
  };

  const handleCreatePlaylist = async () => {
    const selectedTracks = {};
    for (const genre of selectedGenres) {
      selectedTracks[genre] = (genreTrackMap[genre] || [])
        .filter((t) => !excludedTrackIds.includes(t.id))
        .map((t) => t.id);
    }

    for (const [id, genre] of Object.entries(manualAssignments)) {
      if (!genre || excludedTrackIds.includes(id)) continue;
      selectedTracks[genre] = selectedTracks[genre] || [];
      if (!selectedTracks[genre].includes(id)) {
        selectedTracks[genre].push(id);
      }
    }
    try {
      const res = await fetch(`${API_BASE_URL}/playlists`, {
        method: "POST",
        mode: "cors",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_id: analysisId,
          confirmation: true,
          selected_tracks: selectedTracks,
          excluded_track_ids: excludedTrackIds,
        }),
      });

      const text = await res.text();
      let data;

      try {
        data = JSON.parse(text);
      } catch {
        throw new Error("Sunucudan geçersiz JSON geldi.");
      }

      if (!res.ok) {
        throw new Error(data?.detail || "Sunucu hatası");
      }

      if (data.status === "success") {
        setMessage("✅ Playlist(ler) başarıyla oluşturuldu.");
      } else {
        setMessage(
          "❌ Playlist oluşturulamadı: " + (data.message || "Bilinmeyen hata"),
        );
      }
    } catch (err) {
      console.error("❌ Playlist oluşturma hatası:", err);
      setMessage("❌ İstek hatası: " + err.message);
    }
  };

  const handleCreateAllPlaylists = async () => {
    setMessage("⏳ Playlistler oluşturuluyor...");
    try {
      const res = await fetch(
        `${API_BASE_URL}/playlists/full-auto`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ analysis_id: analysisId }),
        },
      );

      const data = await res.json();

      if (res.ok && data.status === "success") {
        setMessage(
          `✅ ${data.created_playlists} playlist oluşturuldu. Toplam ${data.total_tracks} şarkı eklendi.`,
        );
      } else {
        throw new Error(
          data?.detail || data?.message || "Playlist oluşturulamadı.",
        );
      }
    } catch (err) {
      console.error("❌ Otomatik playlist hatası:", err);
      setMessage("❌ Hata: " + err.message);
    }
  };

  const chartData = {
    labels: genres.map((g) => g.genre),
    datasets: [
      {
        data: genres.map((g) => g.percentage),
        backgroundColor: genres.map((_, i) => `hsl(${i * 33}, 65%, 50%)`),
        borderColor: "#222",
        borderWidth: 1,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    onClick: (_, elements) => {
      if (!elements.length) return;
      const genre = chartData.labels[elements[0].index];
      toggleGenreSelection(genre);
    },
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          color: "#eee",
          boxWidth: 12,
        },
      },
    },
  };

  return (
    <PageWrapper>
    <div className="bg-[#121212] text-white min-h-screen flex flex-col items-center py-10 px-4 relative">
        <UserMenu />
        <h1 className="text-3xl font-bold mb-6">Analiz Sonuçları</h1>

        {loading ? (
          <p>Yükleniyor...</p>
        ) : error ? (
          <p className="text-red-400">{error}</p>
        ) : genres.length === 0 ? (
          <p className="text-gray-400">Hiç tür verisi bulunamadı.</p>
        ) : (
          <>
            <div className="w-full max-w-xl">
              <Pie data={chartData} options={chartOptions} />
            </div>
            <div className="mt-4 text-center text-sm text-gray-300">
              Toplam {analysisStats.totalTracks} şarkı analiz edildi, {analysisStats.genreCount} tür bulundu.
              {analysisStats.unknownCount > 0 && (
                <span> {analysisStats.unknownCount} şarkının türü belirlenemedi.</span>
              )}
            </div>
          <div className="mt-6">
              <h2 className="text-lg font-semibold mb-2">Seçilen Türler:</h2>
              <div className="flex flex-wrap gap-2">
                {selectedGenres.map((genre) => (
                  <span
                    key={genre}
                    onClick={() => toggleGenreSelection(genre)}
                    className="bg-green-500 text-black px-3 py-1 rounded-full cursor-pointer"
                  >
                    {genre}
                  </span>
                ))}
              </div>
              {selectedGenres.length > 0 ? (
                <ul className="mt-2 text-sm text-gray-300">
                  {selectedGenres.map((g) => (
                    <li key={g}>{g}: {getCountForGenre(g)} şarkı</li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-gray-400">
                  Grafikte bir türe tıklayarak şarkı sayısını görebilirsin.
                </p>
              )}
            </div>

            <SelectionPanel
              genres={genreTrackMap}
              selectedGenres={new Set(selectedGenres)}
              excludedTrackIds={excludedTrackIds}
              toggleExclude={toggleExclude}
              manualAssignments={manualAssignments}
              setManualAssignments={setManualAssignments}
            />

            <button
              onClick={handleCreatePlaylist}
              disabled={selectedGenres.length === 0}
              className={`mt-6 px-6 py-2 font-bold rounded-full transition duration-300 ease-in-out ${
                selectedGenres.length > 0
                  ? "bg-green-500 hover:bg-green-600 text-black"
                  : "bg-gray-600 text-gray-300 cursor-not-allowed"
              }`}
            >
              Seçilen Türlerden Playlist Oluştur
            </button>

            <button
              onClick={handleCreateAllPlaylists}
              className="mt-4 bg-blue-500 hover:bg-blue-600 text-black font-bold py-2 px-6 rounded-full transition duration-300 ease-in-out"
            >
              Tüm Şarkılar İçin Playlist Oluştur
            </button>

            {message && (
              <p className="mt-4 text-yellow-400 text-center text-lg">
                {message}
              </p>
            )}
          </>
        )}
      </div>
    </PageWrapper>
  );
}

export default ResultPage;
