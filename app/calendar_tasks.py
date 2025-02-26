from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    session,
    redirect,
    url_for,
)
from functools import wraps
from firebase_admin import firestore
import uuid
from datetime import datetime

# Criar o Blueprint
calendar_tasks = Blueprint("calendar_tasks", __name__)


# Middleware de autenticação
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)

    return decorated_function


# Rotas do Calendário
@calendar_tasks.route("/calendar")
@login_required
def calendar():
    return render_template("calendar.html")


@calendar_tasks.route('/api/events', methods=['GET'])
@login_required
def get_events():
    try:
        db = firestore.client()
        user_id = session['user_id']
        
        # Buscar eventos do usuário
        events = db.collection('events').where('user_id', '==', user_id).stream()
        
        events_list = []
        for event in events:
            event_data = event.to_dict()
            events_list.append({
                'id': event.id,
                'title': event_data['title'],
                'start': event_data['start_time'],
                'end': event_data['start_time'],  # Usando mesmo horário para início e fim
                'extendedProps': {
                    'description': event_data.get('description', ''),
                    'appointment_value': event_data.get('appointment_value', 0),
                    'payment_method': event_data.get('payment_method', ''),
                    'payment_status': event_data.get('payment_status', 'pending')
                }
            })
        
        return jsonify(events_list)
    except Exception as e:
        print(f"Erro ao buscar eventos: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@calendar_tasks.route('/api/events', methods=['POST'])
@login_required
def create_event():
    try:
        db = firestore.client()
        data = request.json
        user_id = session['user_id']
        
        # Validar dados obrigatórios
        required_fields = ['title', 'start_time', 'appointment_value', 'payment_method', 'payment_status']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Campo obrigatório ausente: {field}'
                }), 400

        event_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()
        
        # Preparar dados do evento
        event_data = {
            'event_id': event_id,
            'user_id': user_id,
            'title': data['title'],
            'start_time': data['start_time'],
            'description': data.get('description', ''),
            'appointment_value': float(data['appointment_value']),
            'payment_method': data['payment_method'],
            'payment_status': data['payment_status'],
            'created_at': current_time,
            'updated_at': current_time
        }
        
        # Salvar evento
        db.collection('events').document(event_id).set(event_data)
        
        # Criar registro financeiro automaticamente
        financial_record = {
            'record_id': str(uuid.uuid4()),
            'event_id': event_id,
            'user_id': user_id,
            'patient_name': data['title'],
            'appointment_value': float(data['appointment_value']),
            'payment_method': data['payment_method'],
            'appointment_date': data['start_time'],
            'status': data['payment_status'],
            'notes': data.get('description', ''),
            'created_at': current_time,
            'updated_at': current_time
        }
        
        db.collection('financial_records').document(financial_record['record_id']).set(financial_record)
        
        return jsonify({
            'status': 'success',
            'event': {
                'id': event_id,
                'title': event_data['title'],
                'start': event_data['start_time'],
                'extendedProps': {
                    'description': event_data['description'],
                    'appointment_value': event_data['appointment_value'],
                    'payment_method': event_data['payment_method'],
                    'payment_status': event_data['payment_status']
                }
            }
        })
    except Exception as e:
        print(f"Erro ao criar evento: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@calendar_tasks.route('/api/events/<event_id>', methods=['PUT'])
@login_required
def update_event(event_id):
    try:
        db = firestore.client()
        data = request.json
        user_id = session['user_id']
        
        # Verificar se o evento existe e pertence ao usuário
        event_ref = db.collection('events').document(event_id)
        event = event_ref.get()
        
        if not event.exists:
            return jsonify({'status': 'error', 'message': 'Evento não encontrado'}), 404
        
        event_data = event.to_dict()
        if event_data['user_id'] != user_id:
            return jsonify({'status': 'error', 'message': 'Não autorizado'}), 403
        
        # Atualizar dados do evento
        update_data = {
            'title': data['title'],
            'start_time': data['start_time'],
            'description': data.get('description', ''),
            'appointment_value': float(data['appointment_value']),
            'payment_method': data['payment_method'],
            'payment_status': data['payment_status'],
            'updated_at': datetime.utcnow().isoformat()
        }
        
        event_ref.update(update_data)
        
        # Atualizar registro financeiro correspondente
        financial_record = db.collection('financial_records').where('event_id', '==', event_id).limit(1).stream()
        for record in financial_record:
            record.reference.update({
                'patient_name': data['title'],
                'appointment_value': float(data['appointment_value']),
                'payment_method': data['payment_method'],
                'appointment_date': data['start_time'],
                'status': data['payment_status'],
                'notes': data.get('description', ''),
                'updated_at': datetime.utcnow().isoformat()
            })
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Erro ao atualizar evento: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@calendar_tasks.route('/api/events/<event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    try:
        db = firestore.client()
        user_id = session['user_id']
        
        # Verificar se o evento existe e pertence ao usuário
        event_ref = db.collection('events').document(event_id)
        event = event_ref.get()
        
        if not event.exists:
            return jsonify({'status': 'error', 'message': 'Evento não encontrado'}), 404
        
        event_data = event.to_dict()
        if event_data['user_id'] != user_id:
            return jsonify({'status': 'error', 'message': 'Não autorizado'}), 403
        
        # Excluir evento
        event_ref.delete()
        
        # Excluir registro financeiro correspondente
        financial_records = db.collection('financial_records').where('event_id', '==', event_id).stream()
        for record in financial_records:
            record.reference.delete()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Erro ao excluir evento: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# Rotas de Tarefas
@calendar_tasks.route("/tasks")
@login_required
def tasks():
    return render_template("tasks.html")


@calendar_tasks.route("/api/tasks", methods=["GET"])
@login_required
def get_tasks():
    try:
        db = firestore.client()
        user_id = session["user_id"]

        tasks_ref = db.collection("tasks")
        tasks = tasks_ref.where("user_id", "==", user_id).stream()

        tasks_list = []
        for task in tasks:
            task_data = task.to_dict()
            print("Task data:", task_data)  # Adicione este log
            tasks_list.append(
                {
                    "task_id": task_data.get("task_id"),
                    "title": task_data.get("title"),
                    "description": task_data.get("description", ""),
                    "due_date": task_data.get("due_date"),
                    "status": task_data.get("status", "pending"),
                    "priority": task_data.get("priority", "medium"),
                    "created_at": task_data.get("created_at"),
                    "updated_at": task_data.get("updated_at"),
                }
            )

        return jsonify(tasks_list)
    except Exception as e:
        print(f"Erro ao buscar tarefas: {str(e)}")  # Log para debug
        return jsonify({"status": "error", "message": str(e)}), 500


@calendar_tasks.route("/api/tasks", methods=["POST"])
@login_required
def create_task():
    try:
        db = firestore.client()
        data = request.json
        user_id = session["user_id"]

        task_id = str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "title": data["title"],
            "description": data.get("description", ""),
            "due_date": data.get("due_date"),
            "status": data.get("status", "pending"),
            "priority": data.get("priority", "normal"),
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        db.collection("tasks").document(task_id).set(task_data)
        return jsonify({"status": "success", "task": task_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@calendar_tasks.route("/api/tasks/<task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    try:
        db = firestore.client()
        data = request.json
        user_id = session["user_id"]

        print(f"Atualizando tarefa {task_id} com dados: {data}")  # Log para debug

        task_ref = db.collection("tasks").document(task_id)
        task_doc = task_ref.get()

        if task_doc.exists and task_doc.to_dict().get("user_id") == user_id:
            update_data = {
                "title": data.get("title"),
                "description": data.get("description", ""),
                "due_date": data.get("due_date"),  # Corrigido de dueDate para due_date
                "status": data.get("status", "pending"),
                "priority": data.get("priority", "medium"),
                "updated_at": datetime.utcnow().isoformat(),
            }
            # Remover campos None do dicionário
            update_data = {k: v for k, v in update_data.items() if v is not None}

            task_ref.update(update_data)

            # Buscar a tarefa atualizada para retornar
            updated_task = task_ref.get().to_dict()
            return jsonify(
                {
                    "status": "success",
                    "message": "Tarefa atualizada com sucesso",
                    "task": updated_task,
                }
            )

        return jsonify({"status": "error", "message": "Tarefa não encontrada"}), 404
    except Exception as e:
        print(f"Erro ao atualizar tarefa: {str(e)}")  # Log para debug
        return jsonify({"status": "error", "message": str(e)}), 500


@calendar_tasks.route("/api/tasks/<task_id>", methods=["GET"])
@login_required
def get_task(task_id):
    try:
        db = firestore.client()
        user_id = session["user_id"]

        task_ref = db.collection("tasks").document(task_id)
        task_doc = task_ref.get()

        if task_doc.exists and task_doc.to_dict().get("user_id") == user_id:
            task_data = task_doc.to_dict()
            return jsonify(task_data)

        return jsonify({"status": "error", "message": "Tarefa não encontrada"}), 404
    except Exception as e:
        print(f"Erro ao buscar tarefa: {str(e)}")  # Log para debug
        return jsonify({"status": "error", "message": str(e)}), 500


@calendar_tasks.route("/api/tasks/<task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    try:
        db = firestore.client()
        user_id = session["user_id"]

        task_ref = db.collection("tasks").document(task_id)
        task_doc = task_ref.get()

        if task_doc.exists and task_doc.to_dict().get("user_id") == user_id:
            task_ref.delete()
            return jsonify(
                {"status": "success", "message": "Tarefa excluída com sucesso"}
            )

        return jsonify({"status": "error", "message": "Tarefa não encontrada"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
