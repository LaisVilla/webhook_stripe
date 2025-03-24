from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from cloudinary import config as cloudinary_config
import stripe
import os
import json

def create_app():
    app = Flask(__name__)
    
    # Carregar variáveis de ambiente do arquivo .env (para desenvolvimento local)
    load_dotenv(override=True)
    
    # Carregar configuração
    app.config.from_object('app.config.Config')
    
    # Configurar secret key
    app.secret_key = app.config.get('SECRET_KEY') or os.getenv('SECRET_KEY')
    
    # Verificação e configuração de variáveis de ambiente críticas
    def check_env_var(var_name):
        value = os.getenv(var_name)
        if not value:
            print(f"WARNING: {var_name} not found!")
        return value

    # Configuração do Cloudinary
    cloudinary_config(
        cloud_name=check_env_var('CLOUDINARY_CLOUD_NAME'),
        api_key=check_env_var('CLOUDINARY_API_KEY'),
        api_secret=check_env_var('CLOUDINARY_API_SECRET')
    )

    # Configuração do Firebase
    try:
        # Tentar carregar credenciais do Firebase de variável de ambiente
        firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS')
        
        if firebase_creds_json:
            # Se as credenciais estiverem como string JSON na variável de ambiente
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Fallback para arquivo de credenciais (para desenvolvimento local)
            cred_path = os.path.join(os.path.dirname(__file__), 'firebase-adminsdk.json')
            cred = credentials.Certificate(cred_path)
        
        firebase_admin.initialize_app(cred)
        app.db = firestore.client()
    except Exception as e:
        print(f"ERROR configuring Firebase: {e}")
        app.db = None

    # Configuração do OpenAI API Key
    openai_api_key = check_env_var('OPENAI_API_KEY')

    # Configuração da Stripe
    stripe.api_key = app.config.get('STRIPE_SECRET_KEY') or check_env_var('STRIPE_SECRET_KEY')

    # Registrar blueprints
    from .routes import main as main_blueprint
    from .financial import financial
    from .calendar_tasks import calendar_tasks as calendar_tasks_blueprint
    
    app.register_blueprint(main_blueprint)
    app.register_blueprint(calendar_tasks_blueprint)
    app.register_blueprint(financial)  
    
    return app