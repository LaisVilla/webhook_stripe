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
import logging
from .routes import main as main_blueprint
from .financial import financial
from .calendar_tasks import calendar_tasks as calendar_tasks_blueprint
from .health import health

# Configuração global de logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # Salvar em arquivo
        logging.StreamHandler()  # Exibir no console
    ]
)

# Criamos o scheduler como uma variável global
scheduler = APScheduler()
scheduler_initialized = False  # Flag para evitar múltiplas inicializações


def initialize_firebase():
    """Inicializa o Firebase com credenciais locais ou de variável de ambiente."""
    try:
        firebase_admin.get_app()
        logging.info("Firebase já está inicializado.")
        return True
    except ValueError:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cred_path = os.path.join(base_dir, "firebase-adminsdk.json")

            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logging.info("Firebase inicializado via arquivo local.")
                return True

            firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if firebase_creds_json:
                cred_dict = json.loads(firebase_creds_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logging.info("Firebase inicializado via variável de ambiente.")
                return True

            logging.error("Nenhuma credencial do Firebase encontrada.")
            return False

        except Exception as e:
            logging.error(f"Erro ao inicializar Firebase: {e}")
            return False


def create_app():
    global scheduler_initialized

    app = Flask(__name__)

    # Carregar variáveis de ambiente
    load_dotenv(override=True)

    # Configuração do Flask
    app.config.from_object("app.config.Config")

    # Configuração do Scheduler
    app.config.update(
        SCHEDULER_API_ENABLED=True,
        SCHEDULER_TIMEZONE="America/Sao_Paulo"
    )

    # Configuração da chave secreta
    app.secret_key = app.config.get("SECRET_KEY") or os.getenv("SECRET_KEY")

    # Inicialização do Firebase
    if initialize_firebase():
        try:
            app.db = firestore.client()
            logging.info("Firestore inicializado com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao criar cliente Firestore: {e}")
            app.db = None
    else:
        logging.error("Não foi possível inicializar o Firebase.")
        app.db = None

    # Configuração do Cloudinary
    cloudinary_config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET")
    )

    # Configuração do Stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    # Registrar Blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(calendar_tasks_blueprint)
    app.register_blueprint(financial)
    app.register_blueprint(health)

    # Configurar scheduler apenas se ainda não foi inicializado
    if not scheduler_initialized:
        def health_check_job():
            """Executa o health check e registra no logging a cada 1 minuto."""
            with app.app_context():
                try:
                    with app.test_client() as client:
                        response = client.get("/health")
                        current_time = datetime.now(pytz.timezone("America/Sao_Paulo"))

                        if response.status_code == 200:
                            data = response.get_json()
                            logging.info(
                                f"[Health Check] {current_time.strftime('%Y-%m-%d %H:%M:%S')} | "
                                f"Status: {data['status']} | Firebase: {data['firebase']}"
                            )
                        else:
                            logging.warning(
                                f"[Health Check] {current_time.strftime('%Y-%m-%d %H:%M:%S')} | "
                                f"Falha no health check - Status: {response.status_code}"
                            )
                except Exception as e:
                    logging.error(f"[Health Check] Erro: {str(e)}")

        # Inicializar scheduler
        scheduler.init_app(app)

        # Adicionar job do health check para rodar a cada 1 minuto
        scheduler.add_job(
            id="health_check",
            func=health_check_job,
            trigger="interval",
            minutes=1,  # Agora executa a cada 1 minuto
            replace_existing=True
        )

        # Iniciar o scheduler se ainda não estiver rodando
        if not scheduler.running:
            scheduler.start()
            logging.info("[Scheduler] Iniciado com sucesso.")
            logging.info("[Scheduler] Health Check configurado para rodar a cada 1 minuto.")

        # Marcar como inicializado
        scheduler_initialized = True

    return app