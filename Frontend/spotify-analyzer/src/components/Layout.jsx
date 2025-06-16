import { Outlet, Link } from 'react-router-dom';
import { useContext } from 'react';
import UserMenu from './UserMenu.jsx';
import { UserContext } from '../UserContext.jsx';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function Layout() {
  const { isLoggedIn } = useContext(UserContext);

  return (
    <div className="min-h-screen bg-black text-white">
      <header className="fixed top-0 left-0 right-0 bg-black flex justify-between items-center p-4 z-20">
        <Link to="/" className="text-lg font-bold">Genre Analyzer</Link>
        {isLoggedIn ? (
          <UserMenu />
        ) : (
          <a
            href={`${API_BASE_URL}/login`}
            className="text-sm bg-green-500 hover:bg-green-600 text-black font-semibold py-1 px-3 rounded"
          >
            Giriş Yap
          </a>
        )}
      </header>
      <main className="pt-16">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
