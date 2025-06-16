import { Outlet } from 'react-router-dom';
import UserMenu from './UserMenu.jsx';

function Layout() {
  return (
    <div className="min-h-screen bg-black text-white">
      <header className="fixed top-0 left-0 right-0 bg-gray-900 flex justify-end p-4 z-20">
        <UserMenu />
      </header>
      <main className="pt-16">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
