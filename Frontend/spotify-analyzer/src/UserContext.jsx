import { createContext, useState } from 'react';

export const UserContext = createContext({
  profile: null,
  isLoggedIn: false,
  setProfile: () => {},
  setIsLoggedIn: () => {},
});

export function UserProvider({ children }) {
  const [profile, setProfile] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return (
    <UserContext.Provider value={{ profile, setProfile, isLoggedIn, setIsLoggedIn }}>
      {children}
    </UserContext.Provider>
  );
}
