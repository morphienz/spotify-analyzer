# .cache dosyasını silin veya cache klasörünü temizleyin
import os
if os.path.exists(".cache"):
    os.remove(".cache")