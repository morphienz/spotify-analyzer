import os
if os.path.exists(".cache"):
    os.remove(".cache")
print("[*] Token cache temizlendi")