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
    except ValueError:
        # Se não existir, inicializa
        firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS')
        
        if firebase_creds_json:
            # Se as credenciais estiverem como string JSON na variável de ambiente
            try:
                cred_dict = json.loads(firebase_creds_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("Firebase inicializado com sucesso via variável de ambiente")
            except Exception as e:
                print(f"Erro ao inicializar Firebase com variável de ambiente: {e}")
        else:
            print("Erro: Credenciais do Firebase não encontradas")

# Chama a inicialização global antes de criar o app
initialize_firebase()

def create_app():
    app = Flask(__name__)
    
    # Carregar variáveis de ambiente do arquivo .env (para desenvolvimento local)
    load_dotenv(override=True)
    
    # Carregar configuração
    app.config.from_object('app.config.Config')
    
    # Configurar secret key
    app.secret_key = app.config.get('SECRET_KEY') or os.getenv('SECRET_KEY')
    
    try:
        app.db = firestore.client()
    except Exception as e:
        print(f"Erro ao criar cliente Firestore: {e}")
        app.db = None

    # Configuração do Cloudinary
    cloudinary_config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET')
    )

    # Verificar se a chave foi carregada corretamente
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"API key loaded successfully: {api_key[:10]}...")
    else:
        print("WARNING: API key not found!")

    # Configuração do Firebase
    cred_path = app.config['FIREBASE_CREDENTIALS_PATH']
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    app.db = firestore.client()

    # Configuração da Stripe
    stripe.api_key = app.config['STRIPE_SECRET_KEY']

    # Registrar o blueprint
    
    app.register_blueprint(main_blueprint)
    app.register_blueprint(calendar_tasks_blueprint)
    app.register_blueprint(financial)  
    

    return app