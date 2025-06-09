# Bu dosya sadece cache’i temizlemek içindir
import os
if os.path.exists("genre_cache.json"):
    os.remove("genre_cache.json")
    print("Cache dosyası silindi.")
else:
    print("Cache zaten yok.")
