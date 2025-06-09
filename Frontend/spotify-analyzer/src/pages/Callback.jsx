import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function CallbackPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const loginSuccess = params.get("login");

    if (loginSuccess === "success") {
      // Kullanıcı başarılı giriş yaptıysa localStorage'a yaz
      localStorage.setItem("isLoggedIn", "true");

      // 1 saniye bekleyip anasayfaya yönlendir
      setTimeout(() => {
        navigate('/');
      }, 1000);
    } else {
      // Hatalı yönlendirme olursa hata sayfasına gönder
      navigate('/error'); // varsa
    }
  }, [navigate]);

  return (
    <div className="flex items-center justify-center h-screen bg-[#191414] text-white text-xl">
      Spotify hesabınız bağlandı, yönlendiriliyorsunuz...
    </div>
  );
}

export default CallbackPage;
