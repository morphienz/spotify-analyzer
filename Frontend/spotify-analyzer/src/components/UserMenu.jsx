import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';

function UserMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  const name = localStorage.getItem('userName') || 'Kullanıcı';
  const image =
    localStorage.getItem('userImage') ||
    '/vite.svg';

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('isLoggedIn');
    navigate('/');
  };

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
