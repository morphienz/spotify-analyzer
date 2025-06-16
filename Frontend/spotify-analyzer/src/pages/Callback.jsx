import { useEffect, useContext, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchUserProfile } from '../api.js';
import { UserContext } from '../UserContext.jsx';
import PageWrapper from '../components/PageWrapper.jsx';

function CallbackPage() {
  const navigate = useNavigate();
  const { setIsLoggedIn, setProfile } = useContext(UserContext);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const loginSuccess = params.get("login");

    if (loginSuccess === "success") {
      localStorage.setItem("isLoggedIn", "true");
      setIsLoggedIn(true);

      fetchUserProfile()
        .then((profile) => setProfile(profile))
        .catch((e) => console.error("Profile fetch error", e))
        .finally(() => {
          setTimeout(() => {
            navigate('/analyze');
          }, 1000);
        });
    } else {
      const errorMsg = params.get('error') || 'Giriş başarısız';
      setError(errorMsg);
    }
  }, [navigate, setIsLoggedIn, setProfile]);

  return (
    <PageWrapper>
      <div className="flex items-center justify-center h-screen bg-[#191414] text-white text-xl">
        {error ? `Hata: ${error}` : 'Spotify hesabınız bağlandı, yönlendiriliyorsunuz...'}
      </div>
    </PageWrapper>
  );
}

export default CallbackPage;
