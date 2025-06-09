# test_mongo_save.py
from data_store import save_user_tracks, load_user_tracks

dummy_tracks = [
    {"id": "track1", "name": "Deneme Şarkı 1", "artist": "Deneme Sanatçı"},
    {"id": "track2", "name": "Deneme Şarkı 2", "artist": "Deneme Sanatçı"}
]

user_id = "test_user_123"

# Kaydet
save_user_tracks(user_id, dummy_tracks)
print("🎯 Kaydedildi")

# Yükle
loaded = load_user_tracks(user_id)
print("📦 Geri Yüklenen Veri:")
print(loaded)

