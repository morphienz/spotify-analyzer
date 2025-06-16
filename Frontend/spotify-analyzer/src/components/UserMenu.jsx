import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

function UserMenu() {
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem("isLoggedIn");
    window.location.href = "/";
  };

  return (
    <div className="relative inline-block text-left">
      <button
        onClick={() => setOpen((o) => !o)}
        className="p-2 rounded-full bg-gray-800 hover:bg-gray-700 transition duration-300 ease-in-out"
      >
        ☰
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute right-0 mt-2 w-32 bg-gray-800 rounded-md shadow-lg overflow-hidden z-10"
          >
            <button
              onClick={handleLogout}
              className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-700 transition duration-300 ease-in-out"
            >
              Çıkış Yap
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default UserMenu;
