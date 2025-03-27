from flask import Blueprint, jsonify
from datetime import datetime
import pytz
from firebase_admin import firestore

health = Blueprint('health', __name__)

def check_firebase():
    try:
        db = firestore.client()
        db.collection('health_checks').document('test').get()
        return True, None
    except Exception as e:
        return False, str(e)

@health.route('/health')
def health_check():
    firebase_status, firebase_error = check_firebase()
    
    response = {
        'status': 'healthy' if firebase_status else 'unhealthy',
        'timestamp': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S'),
        'checks': {
            'firebase': {
                'status': 'healthy' if firebase_status else 'unhealthy',
                'error': firebase_error
            }
        }
    }
    
    return jsonify(response), 200 if firebase_status else 500