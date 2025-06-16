// App.jsx
import { useEffect, useState, useContext } from 'react';
import { motion } from 'framer-motion';
import UserMenu from './components/UserMenu.jsx';
import PageWrapper from './components/PageWrapper.jsx';
import './index.css';
import { UserContext } from './UserContext.jsx';
import { logout as apiLogout, fetchUserProfile } from './api.js';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const slogans = [
  "Türlerin ötesine geç!",
  "Müziğini analiz et.",
  "Spotify zekâsıyla keşfet.",
  "Beğenilerin seni anlatır.",
  "Müzikal haritanı çiziyoruz."
];

function App() {
  const [currentSlogan, setCurrentSlogan] = useState(0);
  const [feedback, setFeedback] = useState("");
  const { isLoggedIn, setIsLoggedIn, setProfile } = useContext(UserContext);

  useEffect(() => {
    const url = new URL(window.location.href);
    const loginSuccess = url.searchParams.get("login");

    if (loginSuccess === "success") {
      localStorage.setItem("isLoggedIn", "true");
      setIsLoggedIn(true);

      fetchUserProfile()
        .then((profile) => setProfile(profile))
        .catch((e) => console.error("Profile fetch error", e));

      setFeedback("Giriş başarılı!");
      setTimeout(() => setFeedback(""), 3000);

      // URL'den ?login=success kısmını temizle
      window.history.replaceState({}, document.title, "/");
    } else {
      setIsLoggedIn(localStorage.getItem("isLoggedIn") === "true");
    }

    const interval = setInterval(() => {
      setCurrentSlogan((prev) => (prev + 1) % slogans.length);
    }, 2500);

    return () => clearInterval(interval);
  }, []);

  const handleButtonClick = () => {
    if (isLoggedIn) {
      // Analiz seçenek sayfasına git (bir sonraki adımda yapılacak)
      window.location.href = "/analyze/liked";
    } else {
      window.location.href = `${API_BASE_URL}/login`;
    }
  };

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch (e) {
      console.error("Logout failed", e);
    } finally {
      localStorage.removeItem("isLoggedIn");
      localStorage.removeItem("userName");
      localStorage.removeItem("userImage");
      setIsLoggedIn(false);
      setProfile(null);
      window.location.href = "/";
    }
  };

  return (
    <PageWrapper>
      <div className="flex flex-col items-center justify-center h-screen bg-gradient-to-br from-black to-gray-900 text-white transition-all duration-500 relative">
      {isLoggedIn && <UserMenu />}
      {feedback && (
        <div className="mt-2 text-sm text-green-400">{feedback}</div>
      )}
      <div className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4 text-center h-12">
        <span className="text-green-500">{slogans[currentSlogan]}</span>
      </div>
      <motion.button
        onClick={handleButtonClick}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="bg-green-500 hover:bg-green-600 text-black font-bold py-3 px-6 rounded-full text-lg transition duration-300 ease-in-out shadow-lg"
      >
        {isLoggedIn ? "Analiz Et" : "Giriş Yap"}
        </motion.button>
        {isLoggedIn && (
          <button
            onClick={handleLogout}
            className="mt-4 text-sm text-gray-300 underline"
          >
            Çıkış Yap
          </button>
        )}
      </div>
    </PageWrapper>
  );
}

export default App;
