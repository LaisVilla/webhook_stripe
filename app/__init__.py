from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from cloudinary import config as cloudinary_config
import stripe
import os

def create_app():
    app = Flask(__name__)
    
    # Carregar variáveis de ambiente do arquivo .env
    load_dotenv(override=True)

    # Carregar configuração
    app.config.from_object('app.config.Config')

    # Configurar secret key
    app.secret_key = app.config['SECRET_KEY']

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
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app