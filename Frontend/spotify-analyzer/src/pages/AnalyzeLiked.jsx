import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import UserMenu from "../components/UserMenu.jsx";
import PageWrapper from "../components/PageWrapper.jsx";

function AnalyzeLiked() {
  const [status, setStatus] = useState("Hazırlanıyor...");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const hasRun = useRef(false); // Aynı isteği 2 kez atmasın diye

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const analyze = async () => {
      try {
        setStatus("Beğenilen şarkılar alınıyor...");
        setProgress(25);

        const res = await fetch(`${import.meta.env.VITE_API_URL}/analyze-liked`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          mode: "cors",
          credentials: "include",
        });

        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`Sunucu hatası: ${res.status} - ${errorText}`);
        }

        const data = await res.json();
        console.log("🔍 Backend yanıtı:", data);

        if (data.status === "success" && data.data?.analysis_id) {
          setStatus("Analiz tamamlandı!");
          setProgress(100);

          setTimeout(() => {
            navigate(`/result/${data.data.analysis_id}`);
          }, 1000);
        } else {
          throw new Error(data.message || "Analiz başarısız.");
        }
      } catch (err) {
        console.error("❌ Hata:", err);
        setError(err.message || "Bilinmeyen bir hata oluştu.");
        setStatus("Hata oluştu");
        setProgress(0);
      }
    };

    analyze();
  }, [navigate]);

  return (
    <PageWrapper>
    <div className="flex flex-col items-center justify-center h-screen text-white bg-black px-4 relative">
      <UserMenu />
      <div className="text-xl mb-4 text-center">{status}</div>


        <div className="w-full max-w-xl h-4 bg-gray-700 rounded overflow-hidden">
          <div
            className="h-full bg-green-500 rounded transition duration-700"
            style={{ width: `${progress}%` }}
          ></div>
        </div>

        {error && (
          <div className="mt-6 text-red-400 text-center max-w-lg">
            ⚠️ {error}
          </div>
        )}
      </div>
    </PageWrapper>
  );
}

export default AnalyzeLiked;
