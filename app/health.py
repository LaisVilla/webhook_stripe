from flask import Blueprint, jsonify, current_app
from datetime import datetime
import pytz
from firebase_admin import firestore
import os
import platform
import requests

health = Blueprint('health', __name__)

def check_firebase():
    try:
        db = firestore.client()
        # Tenta fazer uma operação real no Firebase com timeout
        db.collection('health_checks').document('test').get(timeout=10)
        return True, None
    except Exception as e:
        return False, str(e)

def check_environment():
    """Verifica o ambiente atual da aplicação"""
    try:
        return {
            'environment': os.getenv('FLASK_ENV', 'production'),
            'debug_mode': current_app.debug if current_app else False,
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'gunicorn_timeout': os.getenv('GUNICORN_TIMEOUT', '120'),  # Timeout do Gunicorn
            'request_timeout': '10'  # Timeout das requisições
        }
    except Exception as e:
        return {
            'environment': os.getenv('FLASK_ENV', 'production'),
            'debug_mode': None,
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'gunicorn_timeout': os.getenv('GUNICORN_TIMEOUT', '120'),
            'request_timeout': '10',
            'error': str(e)
        }

def check_services():
    """Verifica o status dos serviços externos"""
    services_status = {
        'firebase': {'status': 'unknown', 'error': None},
        'cloudinary': {'status': 'configured' if os.getenv('CLOUDINARY_CLOUD_NAME') else 'not_configured'},
        'stripe': {'status': 'configured' if os.getenv('STRIPE_SECRET_KEY') else 'not_configured'}
    }
    
    # Verifica Firebase
    firebase_ok, firebase_error = check_firebase()
    services_status['firebase'] = {
        'status': 'healthy' if firebase_ok else 'unhealthy',
        'error': firebase_error
    }
    
    return services_status

@health.route('/health')
def health_check():
    """
    Endpoint de health check que verifica:
    - Status dos serviços externos (Firebase, Cloudinary, Stripe)
    - Informações do ambiente
    - Timestamps em UTC e local
    
    Este endpoint é usado para monitoramento da aplicação e não mantém ela no ar diretamente.
    A aplicação se mantém no ar através do Gunicorn configurado no Procfile e gerenciado 
    pela plataforma de hospedagem (Render).
    
    Timeouts configurados:
    - Requisições: 10 segundos
    - Gunicorn: 120 segundos (configurado via gunicorn -t 120)
    """
    try:
        # Horários
        utc_now = datetime.now(pytz.UTC)
        local_tz = pytz.timezone('America/Sao_Paulo')
        local_now = utc_now.astimezone(local_tz)
        
        # Verifica serviços
        services_status = check_services()
        
        # Determina o status geral
        all_healthy = all(
            service['status'] in ['healthy', 'configured'] 
            for service in services_status.values()
        )
        
        response = {
            'status': 'healthy' if all_healthy else 'unhealthy',
            'timestamp': {
                'utc': utc_now.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'local': local_now.strftime('%Y-%m-%d %H:%M:%S %Z'),
            },
            'environment': check_environment(),
            'services': services_status,
            'application': {
                'uptime': 'available in production',
                'version': os.getenv('APP_VERSION', '1.0.0')
            }
        }
        
        return jsonify(response), 200 if all_healthy else 500
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'timestamp': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'error': str(e)
        }
        return jsonify(error_response), 500