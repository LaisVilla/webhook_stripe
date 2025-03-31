import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', 1000))
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', 0.7))

    # AI Service Configuration
    AI_REQUEST_LIMIT = int(os.getenv('AI_REQUEST_LIMIT', 50))  # Requests per day
    AI_TOKEN_LIMIT = int(os.getenv('AI_TOKEN_LIMIT', 10000))  # Tokens per day
    AI_ENABLED = os.getenv('AI_ENABLED', 'True').lower() == 'true'

    # AI Rate Limiting
    AI_RATE_LIMIT = {
        'basic': {
            'requests_per_day': 10,
            'tokens_per_request': 500
        },
        'pro': {
            'requests_per_day': 50,
            'tokens_per_request': 1000
        },
        'premium': {
            'requests_per_day': 100,
            'tokens_per_request': 2000
        }
    }

    # Stripe Configuration
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_XXXXXXXXXXXXXXXXXXXXXXXX')
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', 'pk_test_XXXXXXXXXXXXXXXXXXXXXXXX')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_XXXXXXXXXXXXXXXXXXXXXXXX')

    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH', 'C:/Users/lvsar/my_flask_app/firebase-adminsdk.json')
    FIREBASE_CONFIG = {
        "apiKey": os.getenv('FIREBASE_API_KEY'),
        "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
        "projectId": os.getenv('FIREBASE_PROJECT_ID'),
        "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
        "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
        "appId": os.getenv('FIREBASE_APP_ID'),
        "databaseURL": os.getenv('FIREBASE_DATABASE_URL')
    }

    # Available Plans (Updated with AI features)
    PLANS = {
        'basic': {
            'name': 'Basic Plan',
            'price': 2900,  # in cents, $29.00
            'description': 'Ideal for beginners',
            'ai_features': {
                'daily_requests': 10,
                'max_tokens': 500,
                'models': ['gpt-3.5-turbo']
            }
        },
        'pro': {
            'name': 'Pro Plan',
            'price': 4900,  # in cents, $49.00
            'description': 'For professionals',
            'ai_features': {
                'daily_requests': 50,
                'max_tokens': 1000,
                'models': ['gpt-3.5-turbo']
            }
        },
        'premium': {
            'name': 'Premium Plan',
            'price': 8900,  # in cents, $89.00
            'description': 'Complete resources',
            'ai_features': {
                'daily_requests': 100,
                'max_tokens': 2000,
                'models': ['gpt-3.5-turbo', 'gpt-4']
            }
        }
    }

    # Check if in development environment
    DEVELOPMENT = os.environ.get('FLASK_ENV') == 'development'

    # Base URL of the application for health checks
    if DEVELOPMENT:
        APP_URL = 'http://127.0.0.1:5000'  # Local URL
    else:
        APP_URL = 'https://nexusai-unq0.onrender.com'  # Production URL

    # Override via environment variable
    APP_URL = os.getenv('APP_URL', APP_URL)

    # Health check interval in seconds
    HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 10))

    # Additional settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # AI Service Cache Configuration
    AI_CACHE_ENABLED = os.getenv('AI_CACHE_ENABLED', 'True').lower() == 'true'
    AI_CACHE_TIMEOUT = int(os.getenv('AI_CACHE_TIMEOUT', 3600))  # 1 hour in seconds

    # AI Request Tracking
    AI_TRACKING = {
        'log_requests': True,
        'log_responses': True,
        'store_history': True,
        'history_retention_days': 30
    }

    # AI Error Messages
    AI_ERROR_MESSAGES = {
        'rate_limit': 'You have reached your daily request limit. Please upgrade your plan or try again tomorrow.',
        'token_limit': 'You have reached your daily token limit. Please upgrade your plan or try again tomorrow.',
        'service_unavailable': 'AI service is temporarily unavailable. Please try again later.',
        'invalid_input': 'Invalid input provided. Please check your request and try again.',
        'unauthorized': 'Unauthorized access. Please check your subscription status.'
    }