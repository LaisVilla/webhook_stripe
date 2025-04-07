from flask import Flask
import json
from flask import Flask
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from cloudinary import config as cloudinary_config
import stripe
import os
from flask_apscheduler import APScheduler
from datetime import datetime  
import pytz
from .routes import main as main_blueprint
from .financial import financial
from .calendar_tasks import calendar_tasks as calendar_tasks_blueprint
from .health import health
import logging
from app.utils.health_check import init_health_check



#scheduler = APScheduler()

def initialize_firebase():
    try:
        firebase_admin.get_app()
        print("Firebase já está inicializado")
        return True
    except ValueError:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cred_path = os.path.join(base_dir, 'firebase-adminsdk.json')
            
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print(f"Firebase inicializado com sucesso via arquivo local")
                return True
            
            firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
            if firebase_creds_json:    
                cred_dict = json.loads(firebase_creds_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("Firebase inicializado com sucesso via FIREBASE_CREDENTIALS_JSON")
                return True
            
            print("Erro: Nenhuma credencial do Firebase encontrada")
            return False
            
        except Exception as e:
            print(f"Erro na inicialização do Firebase: {e}")
            return False

def create_app():
    app = Flask(__name__)
    
    # Carregar variáveis de ambiente
    load_dotenv(override=True)
    
    # Carregar configuração
    app.config.from_object('app.config.Config')

    logging.basicConfig(level= logging.INFO)
    logger = logging.getLogger(__name__)

    init_health_check()

    # Adicionar configurações do scheduler
    app.config.update(
        SCHEDULER_API_ENABLED=True,
        SCHEDULER_TIMEZONE="America/Sao_Paulo"  # Ajustado para seu fuso horário
    )

    # Configurar secret key
    app.secret_key = app.config.get('SECRET_KEY') or os.getenv('SECRET_KEY')
    
    # Inicializar Firebase
    if initialize_firebase():
        try:
            app.db = firestore.client()
            print("Firestore cliente inicializado com sucesso")
        except Exception as e:
            print(f"Erro ao criar cliente Firestore: {e}")
            app.db = None
    else:
        print("Não foi possível inicializar o Firebase")
        app.db = None

    
    # Configuração do Stripe
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    # Registrar blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(calendar_tasks_blueprint)
    app.register_blueprint(financial)
    app.register_blueprint(health)

    return app