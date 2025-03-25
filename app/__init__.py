from flask import Flask
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from cloudinary import config as cloudinary_config
import stripe
import os
from .routes import main as main_blueprint
from .financial import financial
from .calendar_tasks import calendar_tasks as calendar_tasks_blueprint

# Inicialização global do Firebase
def initialize_firebase():
    try:
        # Tenta obter o app existente
        firebase_admin.get_app()
        print("Firebase já está inicializado")
    except ValueError:
        try:
            # Tenta obter as credenciais da variável de ambiente
            firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
            
            if not firebase_creds_json:
                print("Erro: FIREBASE_CREDENTIALS_JSON não encontrada")
                return False
            
            try:
                # Converte a string JSON em dicionário
                cred_dict = json.loads(firebase_creds_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("Firebase inicializado com sucesso via FIREBASE_CREDENTIALS_JSON")
                return True
            except json.JSONDecodeError as e:
                print(f"Erro ao decodificar JSON das credenciais: {e}")
                return False
            except Exception as e:
                print(f"Erro ao inicializar Firebase: {e}")
                return False
        except Exception as e:
            print(f"Erro geral na inicialização do Firebase: {e}")
            return False

def create_app():
    app = Flask(__name__)
    
    # Carregar variáveis de ambiente
    load_dotenv(override=True)
    
    # Carregar configuração
    app.config.from_object('app.config.Config')
    
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

    # Configuração do Cloudinary
    cloudinary_config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET')
    )

    # Verificar se a chave OpenAI foi carregada
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"OpenAI API key loaded successfully: {api_key[:5]}...")
    else:
        print("WARNING: OpenAI API key not found!")

    # Configuração do Stripe
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    # Registrar blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(calendar_tasks_blueprint)
    app.register_blueprint(financial)

    return app