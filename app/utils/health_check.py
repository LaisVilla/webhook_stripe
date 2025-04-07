# app/utils/health_check.py
import requests
import time
from datetime import datetime
import logging
import os
from threading import Thread

logger = logging.getLogger(__name__)

def ping_server():
    """
    Function to periodically ping the server to keep it alive
    """
    # Use a URL de produção por padrão, mas permita sobrescrever com variável de ambiente
    app_url = os.getenv('APP_URL', 'https://nexusai-unq0.onrender.com')
    # Remove a barra final se existir para evitar double slash
    app_url = app_url.rstrip('/')
    logger.info(f"Iniciando health check para: {app_url}")
    
    while True:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            response = requests.get(
                f"{app_url}/health",
                timeout=60,  # Adiciona um timeout para evitar esperas muito longas
                headers={'User-Agent': 'NexusAi-HealthCheck/1.0'}
            )
            logger.info(f"[{current_time}] Health check ping: {response.status_code}")
        except Exception as e:
            logger.error(f"[{current_time}] Health check failed: {str(e)}")
        # Wait for 10 minutes before the next ping
        time.sleep(600)

def start_health_check():
    """
    Starts the health check in a background thread
    """
    thread = Thread(target=ping_server, daemon=True)
    thread.start()
    logger.info("Health check thread started")

# Alias para manter compatibilidade
init_health_check = start_health_check