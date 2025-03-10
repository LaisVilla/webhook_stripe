from flask import Blueprint, render_template, jsonify, request, session
from functools import wraps
from firebase_admin import firestore
from datetime import datetime, timedelta
import uuid
from .routes import login_required


financial = Blueprint('financial', __name__)

@financial.route('/financial')
@login_required
def financial_dashboard():
    return render_template('financial.html')

@financial.route('/api/financial/dashboard-data')
@login_required
def get_dashboard_data():
    """Retorna dados para o dashboard financeiro."""
    try:
        db = firestore.client()
        user_id = session.get('user_id')
        
        # Definir período (mês atual)
        now = datetime.utcnow()
        start_date = datetime(now.year, now.month, 1)
        if now.month == 12:
            end_date = datetime(now.year + 1, 1, 1)
        else:
            end_date = datetime(now.year, now.month + 1, 1)

        print(f"Buscando dados para período: {start_date.isoformat()} até {end_date.isoformat()}")
        
        # Buscar registros financeiros
        records = db.collection('financial_records')\
            .where("user_id", "==", user_id)\
            .where("appointment_date", ">=", start_date.isoformat())\
            .where("appointment_date", "<", end_date.isoformat())\
            .stream()
        
        records = list(records)
        print(f"Encontrados {len(records)} registros")
        
        # Inicializar dados
        dashboard_data = {
            'financial_summary': {
                'total_revenue': 0,
                'total_appointments': len(records),
                'pending_payments': 0,
                'average_value': 0
            },
            'daily_statistics': {},
            'revenue_by_payment_method': {},
            'completion_rate': 0
        }
        
        # Processar registros
        completed_records = 0
        
        for record in records:
            data = record.to_dict()
            value = float(data.get('appointment_value', 0))
            
            # Atualizar resumo financeiro
            dashboard_data['financial_summary']['total_revenue'] += value
            
            if data.get('status') == 'pending':
                dashboard_data['financial_summary']['pending_payments'] += value
            elif data.get('status') == 'paid':
                completed_records += 1
            
            # Atualizar estatísticas por método de pagamento
            payment_method = data.get('payment_method')
            if payment_method:
                if payment_method not in dashboard_data['revenue_by_payment_method']:
                    dashboard_data['revenue_by_payment_method'][payment_method] = 0
                dashboard_data['revenue_by_payment_method'][payment_method] += value
            
            # Atualizar estatísticas diárias
            date = data.get('appointment_date', '').split('T')[0]
            if date:
                if date not in dashboard_data['daily_statistics']:
                    dashboard_data['daily_statistics'][date] = {
                        'revenue': 0,
                        'appointments': 0,
                        'completed': 0
                    }
                dashboard_data['daily_statistics'][date]['revenue'] += value
                dashboard_data['daily_statistics'][date]['appointments'] += 1
                if data.get('status') == 'paid':
                    dashboard_data['daily_statistics'][date]['completed'] += 1
        
        # Calcular métricas finais
        total_records = len(records)
        if total_records > 0:
            dashboard_data['completion_rate'] = (completed_records / total_records) * 100
            dashboard_data['financial_summary']['average_value'] = \
                dashboard_data['financial_summary']['total_revenue'] / total_records
        
        return jsonify(dashboard_data)
    except Exception as e:
        print(f"Erro ao buscar dados do dashboard: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@financial.route('/api/financial/records', methods=['GET'])
@login_required
def get_financial_records():
    try:
        db = firestore.client()
        user_id = session.get('user_id')
        
        # Obter filtros da query string
        month_filter = request.args.get('month')
        status_filter = request.args.get('status')
        
        print(f"Filtros aplicados: mês={month_filter}, status={status_filter}")
        
        # Construir query base
        query = db.collection('financial_records').where('user_id', '==', user_id)
        
        # Se tiver filtro de status, usar o índice que inclui status
        if status_filter and status_filter != 'all':
            query = query.where('status', '==', status_filter)
        
        # Ordenar por data
        query = query.order_by('appointment_date', direction=firestore.Query.DESCENDING)
        
        # Aplicar filtro de mês
        if month_filter:
            start_date = f"{month_filter}-01"
            year, month = map(int, month_filter.split('-'))
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{str(month + 1).zfill(2)}-01"
            
            query = query.where('appointment_date', '>=', start_date)\
                        .where('appointment_date', '<', end_date)
        
        # Executar query
        records = list(query.stream())
        records_list = []
        
        for record in records:
            record_data = record.to_dict()
            # Garantir que o ID do documento está incluído
            record_data['record_id'] = record.id
            records_list.append(record_data)
        
        print(f"Registros encontrados: {len(records_list)}")
        # Log para debug
        for record in records_list:
            print(f"Record ID: {record.get('record_id')}, Patient: {record.get('patient_name')}")
        
        return jsonify(records_list)
        
    except Exception as e:
        print(f"Erro ao buscar registros: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'records': []
        }), 500

@financial.route('/api/financial/records', methods=['POST'])
@login_required
def create_financial_record():
    """Cria um novo registro financeiro."""
    try:
        db = firestore.client()
        data = request.json
        user_id = session.get('user_id')
        
        # Validar dados
        required_fields = [
            'patient_name', 'appointment_value', 'appointment_date',
            'payment_method', 'status'
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Campo obrigatório ausente: {field}'
                }), 400
        
        # Criar registro
        record_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()
        
        record_data = {
            'record_id': record_id,
            'user_id': user_id,
            'patient_name': data['patient_name'],
            'appointment_value': float(data['appointment_value']),
            'payment_method': data['payment_method'],
            'appointment_date': data['appointment_date'],
            'status': data['status'],
            'notes': data.get('notes', ''),
            'created_at': current_time,
            'updated_at': current_time
        }
        
        # Salvar no Firestore
        db.collection('financial_records').document(record_id).set(record_data)
        
        return jsonify({
            'status': 'success',
            'record': record_data
        })
    except Exception as e:
        print(f"Erro ao criar registro: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
@financial.route('/api/financial/records/<record_id>', methods=['DELETE'])
@login_required
def delete_financial_record(record_id):
    """Exclui um registro financeiro."""
    try:
        db = firestore.client()
        user_id = session.get('user_id')
        
        # Verificar se o registro existe e pertence ao usuário
        record_ref = db.collection('financial_records').document(record_id)
        record = record_ref.get()
        
        if not record.exists:
            return jsonify({
                'status': 'error',
                'message': 'Registro não encontrado'
            }), 404
        
        record_data = record.to_dict()
        if record_data.get('user_id') != user_id:
            return jsonify({
                'status': 'error',
                'message': 'Não autorizado'
            }), 403
        
        # Excluir registro
        record_ref.delete()
        
        return jsonify({
            'status': 'success',
            'message': 'Registro excluído com sucesso'
        })
        
    except Exception as e:
        print(f"Erro ao excluir registro: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    
@financial.route('/api/financial/records/<record_id>', methods=['PUT'])
@login_required
def update_financial_record(record_id):
    """Atualiza um registro financeiro."""
    try:
        db = firestore.client()
        data = request.json
        user_id = session.get('user_id')
        
        # Verificar se o registro existe e pertence ao usuário
        record_ref = db.collection('financial_records').document(record_id)
        record = record_ref.get()
        
        if not record.exists:
            return jsonify({
                'status': 'error',
                'message': 'Registro não encontrado'
            }), 404
        
        record_data = record.to_dict()
        if record_data.get('user_id') != user_id:
            return jsonify({
                'status': 'error',
                'message': 'Não autorizado'
            }), 403
        
        # Atualizar dados
        update_data = {
            'patient_name': data['patient_name'],
            'appointment_value': float(data['appointment_value']),
            'appointment_date': data['appointment_date'],
            'payment_method': data['payment_method'],
            'status': data['status'],
            'notes': data.get('notes', ''),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Salvar alterações
        record_ref.update(update_data)
        
        # Retornar registro atualizado
        updated_record = record_ref.get().to_dict()
        return jsonify({
            'status': 'success',
            'record': updated_record
        })
        
    except Exception as e:
        print(f"Erro ao atualizar registro: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500