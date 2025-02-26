# app/financial.py
from flask import Blueprint, render_template, jsonify, request, session
from functools import wraps
from firebase_admin import firestore
from datetime import datetime
import uuid
from .routes import login_required

financial = Blueprint('financial', __name__)

@financial.route('/financial')
@login_required
def financial_dashboard():
    return render_template('financial.html')

@financial.route('/api/financial/records', methods=['GET'])
@login_required
def get_financial_records():
    try:
        db = firestore.client()
        user_id = session['user_id']
        
        records = db.collection('financial_records')\
            .where('user_id', '==', user_id)\
            .order_by('appointment_date', direction='desc')\
            .stream()
            
        records_list = []
        for record in records:
            record_data = record.to_dict()
            records_list.append(record_data)
            
        return jsonify(records_list)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@financial.route('/api/financial/records', methods=['POST'])
@login_required
def create_financial_record():
    try:
        db = firestore.client()
        data = request.json
        user_id = session['user_id']
        
        record_id = str(uuid.uuid4())
        record_data = {
            'record_id': record_id,
            'user_id': user_id,
            'patient_name': data['patient_name'],
            'appointment_value': float(data['appointment_value']),
            'payment_method': data['payment_method'],
            'appointment_date': data['appointment_date'],
            'status': data['status'],
            'notes': data.get('notes', ''),
            'insurance_info': data.get('insurance_info', {}),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        db.collection('financial_records').document(record_id).set(record_data)
        return jsonify({'status': 'success', 'record': record_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500