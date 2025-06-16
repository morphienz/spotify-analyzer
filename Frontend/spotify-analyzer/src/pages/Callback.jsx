import { useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchUserProfile } from '../api.js';
import { UserContext } from '../UserContext.jsx';
import PageWrapper from '../components/PageWrapper.jsx';

function CallbackPage() {
  const navigate = useNavigate();
  const { setIsLoggedIn, setProfile } = useContext(UserContext);

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
            navigate('/');
          }, 1000);
        });
    } else {
      // Hatalı yönlendirme olursa hata sayfasına gönder
      navigate('/error'); // varsa
    }
  }, [navigate, setIsLoggedIn, setProfile]);

  return (
    <PageWrapper>
      <div className="flex items-center justify-center h-screen bg-[#191414] text-white text-xl">
        Spotify hesabınız bağlandı, yönlendiriliyorsunuz...
      </div>
    </PageWrapper>
  );
}

export default CallbackPage;
