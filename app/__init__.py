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
            # Tenta primeiro usar FIREBASE_CREDENTIALS_JSON
            cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
            if cred_json:
                try:
                    cred_dict = json.loads(cred_json)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    print("Firebase inicializado com sucesso via FIREBASE_CREDENTIALS_JSON")
                    return
                except Exception as e:
                    print(f"Erro ao inicializar Firebase com FIREBASE_CREDENTIALS_JSON: {e}")
            
            # Se não encontrou FIREBASE_CREDENTIALS_JSON, tenta FIREBASE_CREDENTIALS
            firebase_creds = os.getenv('FIREBASE_CREDENTIALS')
            if firebase_creds:
                try:
                    if os.path.isfile(firebase_creds):
                        # Se for um caminho de arquivo válido
                        cred = credentials.Certificate(firebase_creds)
                    else:
                        # Se for uma string JSON
                        cred_dict = json.loads(firebase_creds)
                        cred = credentials.Certificate(cred_dict)
                    
                    firebase_admin.initialize_app(cred)
                    print("Firebase inicializado com sucesso via FIREBASE_CREDENTIALS")
                except Exception as e:
                    print(f"Erro ao inicializar Firebase com FIREBASE_CREDENTIALS: {e}")
            else:
                print("Erro: Nenhuma credencial do Firebase encontrada")
        except Exception as e:
            print(f"Erro na inicialização do Firebase: {e}")

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
    
    # Inicializar Firestore
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

    # Verificar se a chave OpenAI foi carregada corretamente
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"API key loaded successfully: {api_key[:10]}...")
    else:
        print("WARNING: API key not found!")

    # Configuração da Stripe
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    # Registrar os blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(calendar_tasks_blueprint)
    app.register_blueprint(financial)

    return app