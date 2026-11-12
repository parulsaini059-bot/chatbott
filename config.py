import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key-nova-ai-2026')
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Database Configuration
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite').lower()
    
    # Check for direct database URL first
    env_db_url = os.getenv('DATABASE_URL')
    if env_db_url:
        if env_db_url.startswith('postgres://'):
            env_db_url = env_db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = env_db_url
    elif DATABASE_TYPE == 'mysql':
        mysql_user = os.getenv('MYSQL_USER', 'root')
        mysql_pass = os.getenv('MYSQL_PASSWORD', '')
        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        mysql_port = os.getenv('MYSQL_PORT', '3306')
        mysql_db = os.getenv('MYSQL_DB', 'chatbot_db')
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}:{mysql_port}/{mysql_db}"
        )
    else:
        # Default SQLite database - fallback to /tmp in serverless environments (Vercel)
        if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            db_path = Path('/tmp') / 'chatbot.db'
        else:
            db_path = BASE_DIR / 'chatbot.db'
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True
    } if 'mysql' in SQLALCHEMY_DATABASE_URI else {}

    # AI Provider Settings (Default: Google Gemini)
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'gemini').lower()
    
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash').strip()

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip()
    
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '').strip()
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile').strip()

    # Exact required system prompt for General-Purpose AI
    DEFAULT_SYSTEM_PROMPT = (
        "You are NovaAI, an advanced, intelligent, friendly, and highly capable general-purpose AI assistant.\n\n"
        "You can discuss virtually any subject and help users with questions, explanations, calculations, coding, education, writing, reasoning, and everyday tasks.\n\n"
        "You must understand the user’s intent rather than simply matching keywords.\n\n"
        "Always generate responses using your actual language model capabilities.\n\n"
        "Be conversational, accurate, helpful, and context-aware.\n\n"
        "Adapt your response language to the user’s language (e.g. answer in Hindi if asked in Hindi, Hinglish if asked in Hinglish, English if asked in English).\n\n"
        "Do not restrict yourself to a predefined FAQ database.\n\n"
        "Never generate generic filler content.\n\n"
        "Do not claim to have searched the internet or accessed real-time information unless an appropriate tool has actually been used.\n\n"
        "If you do not know something, be transparent.\n\n"
        "Your goal is to provide a ChatGPT-like conversational experience."
    )

    AI_SYSTEM_PROMPT = os.getenv('AI_SYSTEM_PROMPT', DEFAULT_SYSTEM_PROMPT)
