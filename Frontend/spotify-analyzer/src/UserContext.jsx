import { createContext, useState, useEffect } from 'react';

export const UserContext = createContext({
  profile: null,
  isLoggedIn: false,
  setProfile: () => {},
  setIsLoggedIn: () => {},
});

export function UserProvider({ children }) {
  const [profile, setProfile] = useState(() => {
    const stored = localStorage.getItem('profile');
    try {
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [isLoggedIn, setIsLoggedIn] = useState(
    localStorage.getItem('isLoggedIn') === 'true'
  );

  useEffect(() => {
    localStorage.setItem('isLoggedIn', isLoggedIn ? 'true' : 'false');
  }, [isLoggedIn]);

  useEffect(() => {
    if (profile) {
      localStorage.setItem('profile', JSON.stringify(profile));
    } else {
      localStorage.removeItem('profile');
    }
  }, [profile]);

  return (
    <UserContext.Provider value={{ profile, setProfile, isLoggedIn, setIsLoggedIn }}>
      {children}
    </UserContext.Provider>
  );
}
