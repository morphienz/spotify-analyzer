import logging
import os
from logging.handlers import RotatingFileHandler

def configure_logging():
    """Log konfigürasyonunu yapar"""
    # Log klasörü oluştur
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Temel konfigürasyon
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                'logs/application.log',
                maxBytes=1024*1024*5,  # 5 MB
                backupCount=5
            ),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging sistemi başlatıldı")