from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))

try:
    client.admin.command('ping')
    print("✅ MongoDB bağlantısı başarılı")
except Exception as e:
    print(f"❌ Bağlantı hatası: {e}")
