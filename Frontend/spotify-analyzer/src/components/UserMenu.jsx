import { useState, useEffect, useRef, useContext } from "react";
import { Link, useNavigate } from "react-router-dom";
import { logout as apiLogout } from "../api.js";
import { UserContext } from "../UserContext.jsx";

function UserMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();
  const { isLoggedIn, setIsLoggedIn, profile, setProfile } = useContext(UserContext);

  const name =
    profile?.display_name || localStorage.getItem("userName") || "Kullanıcı";
  const image =
    (profile?.images && profile.images[0]?.url) ||
    localStorage.getItem("userImage") ||
    "/vite.svg";

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch (e) {
      console.error("Logout failed", e);
    } finally {
      localStorage.removeItem("isLoggedIn");
      setIsLoggedIn(false);
      setProfile(null);
      navigate("/");
    }
  };

  if (!isLoggedIn) {
    return (
      <button
        onClick={() => {
          window.location.href = `${import.meta.env.VITE_API_URL}/login`;
        }}
        className="px-4 py-2 bg-green-500 text-black rounded-full"
      >
        Giriş Yap
      </button>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <button
        className="flex items-center gap-2 focus:outline-none"
        onClick={() => setOpen(!open)}
      >
        <img src={image} alt="User" className="w-8 h-8 rounded-full" />
        <span className="text-sm font-medium">{name}</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-40 bg-gray-800 text-white rounded shadow-lg z-10">
          <Link
            to="/history"
            className="block px-4 py-2 hover:bg-gray-700"
            onClick={() => setOpen(false)}
          >
            Geçmiş Analizler
          </Link>
          <button
            onClick={handleLogout}
            className="w-full text-left px-4 py-2 hover:bg-gray-700"
          >
            Çıkış Yap
          </button>
        </div>
      )}
    </div>
  );
}

export default UserMenu;
