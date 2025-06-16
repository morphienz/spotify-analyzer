import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

function UserMenu() {
  const [open, setOpen] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(localStorage.getItem("isLoggedIn") === "true");
  }, []);

  if (!loggedIn) return null;

  return (
    <div className="absolute top-4 right-4 text-right">
      <button
        onClick={() => setOpen((o) => !o)}
        className="px-3 py-1 bg-gray-800 text-white rounded"
      >
        ☰
      </button>
      {open && (
        <div className="mt-2 bg-gray-900 text-white rounded shadow-lg p-2">
          <Link
            to="/history"
            onClick={() => setOpen(false)}
            className="block px-4 py-2 hover:bg-gray-700 rounded"
          >
            Analiz Geçmişi
          </Link>
        </div>
      )}
    </div>
  );
}

export default UserMenu;
