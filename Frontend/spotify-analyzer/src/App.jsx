// App.jsx
import { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import UserMenu from './components/UserMenu.jsx';
import PageWrapper from './components/PageWrapper.jsx';
import './index.css';
import { UserContext } from './UserContext.jsx';
import { logout as apiLogout, fetchUserProfile, fetchAuthUrl } from './api.js';
import { API_BASE_URL } from './config.js';

const slogans = [
  "Türlerin ötesine geç!",
  "Müziğini analiz et.",
  "Spotify zekâsıyla keşfet.",
  "Beğenilerin seni anlatır.",
  "Müzikal haritanı çiziyoruz."
];

function App() {
  const [currentSlogan, setCurrentSlogan] = useState(0);
  const [loginMessage, setLoginMessage] = useState("");
  const { isLoggedIn, setIsLoggedIn, setProfile } = useContext(UserContext);
  const navigate = useNavigate();

  useEffect(() => {
    const url = new URL(window.location.href);
    const loginSuccess = url.searchParams.get("login");

  const loggedIn =
      loginSuccess === "success" || localStorage.getItem("isLoggedIn") === "true";

    if (loggedIn) {
      localStorage.setItem("isLoggedIn", "true");
      setIsLoggedIn(true);
      fetchUserProfile()
        .then((p) => setProfile(p))
        .catch((e) => console.error("Profile fetch error", e));

  if (loginSuccess === "success") {
        setLoginMessage("Giriş başarılı!");
      }
    } else {
      setIsLoggedIn(false);
    }

    if (loginSuccess) {
      window.history.replaceState({}, document.title, "/");
    }

    const interval = setInterval(() => {
      setCurrentSlogan((prev) => (prev + 1) % slogans.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [setIsLoggedIn, setProfile]);

  useEffect(() => {
    if (!loginMessage) return;
    const t = setTimeout(() => setLoginMessage(""), 3000);
    return () => clearTimeout(t);
  }, [loginMessage]);

 const handleButtonClick = async () => {
    if (isLoggedIn) {
      navigate("/analyze");
    } else {
      try {
        const authUrl = await fetchAuthUrl();
        window.location.href = authUrl;
      } catch (err) {
        console.error("Login start failed", err);
        setLoginMessage("Giriş başlatılamadı");
      }
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
      {loginMessage && (
        <div className="absolute top-20 text-green-400">{loginMessage}</div>
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
