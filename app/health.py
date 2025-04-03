from flask import Blueprint, jsonify
from firebase_admin import firestore
import pytz
from datetime import datetime

health = Blueprint('health', __name__)

def check_firebase():
    """Verificação simples do Firebase"""
    try:
        db = firestore.client()
        # Faz uma operação simples para verificar a conexão
        db.collection('health_checks').document('test').get(timeout=3)
        return True
    except Exception:
        return False

@health.route('/health')
def health_check():
    """
    Endpoint simplificado de health check que verifica:
    - Status do Firebase
    - Timestamp atual
    """
    try:
        # Verifica Firebase
        firebase_status = check_firebase()
        
        # Timestamp atual
        current_time = datetime.now(pytz.UTC)
        
        response = {
            'status': 'healthy' if firebase_status else 'unhealthy',
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'firebase': 'connected' if firebase_status else 'disconnected'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'error': str(e)
        }), 500