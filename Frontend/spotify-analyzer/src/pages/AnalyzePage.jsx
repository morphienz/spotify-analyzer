import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import UserMenu from "../components/UserMenu.jsx";
import PageWrapper from "../components/PageWrapper.jsx";
import { API_BASE_URL } from "../config.js";

function AnalyzePage() {
  const [status, setStatus] = useState("Hazırlanıyor...");
  const [progress, setProgress] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const analyze = async () => {
      try {
        setStatus("Beğenilen şarkılar alınıyor...");
        setProgress(10);

        const res = await fetch(`${API_BASE_URL}/analyze-liked`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        const text = await res.text();
        const data = JSON.parse(text);
        console.log("🔍 Backend yanıtı:", data);

        if (data.status === "success" && data.data.analysis_id) {
          setStatus("Analiz tamamlandı!");
          setProgress(100);

          // ✅ Sonuç sayfasına yönlendir
          setTimeout(() => {
            navigate(`/result/${data.data.analysis_id}`);
          }, 1000);
        } else {
          throw new Error(data.message || "Analiz başarısız.");
        }
      } catch (err) {
        console.error("❌ Hata:", err);
        setStatus("Hata oluştu: " + err.message);
        setProgress(0);
      }
    };

    analyze();
  }, [navigate]);

  return (
    <PageWrapper>
      <div className="flex flex-col items-center justify-center h-screen text-white bg-black relative">
        <UserMenu />
        <div className="text-xl mb-4">{status}</div>
        <div className="w-1/2 h-4 bg-gray-700 rounded">
          <div
            className="h-full bg-green-500 rounded transition-all duration-700"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>
    </PageWrapper>
  );
}

export default AnalyzePage;
