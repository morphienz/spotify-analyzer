import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchUserAnalyses } from "../api";
import UserMenu from "../components/UserMenu.jsx";

function AnalysisHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchUserAnalyses();
        setHistory(data || []);
      } catch (err) {
        console.error(err);
        setError(err.message || "Veri alınamadı");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center py-10 relative">
      <UserMenu />
      <h1 className="text-3xl font-bold mb-6">Analiz Geçmişi</h1>
      {loading ? (
        <p>Yükleniyor...</p>
      ) : error ? (
        <p className="text-red-400">{error}</p>
      ) : history.length === 0 ? (
        <p>Henüz analiz yapılmamış.</p>
      ) : (
        <ul className="w-full max-w-xl space-y-4">
          {history.map((item) => (
            <li key={item.analysis_id} className="bg-gray-800 p-4 rounded-lg flex justify-between">
              <Link className="text-green-400 hover:underline" to={`/result/${item.analysis_id}`}>{new Date(item.created_at).toLocaleString()}</Link>
              <span className="text-sm text-gray-300">{item.track_count} şarkı / {item.genre_count} tür</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default AnalysisHistory;
