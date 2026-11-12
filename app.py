import os
import logging
from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

from pathlib import Path
from flask import Flask, render_template, jsonify
from flask_login import LoginManager

BASE_DIR = Path(__file__).resolve().parent

from config import Config
from models import db, User
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.conversations import conversations_bp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    """Application factory for NovaAI Chatbot."""
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / 'templates'),
        static_folder=str(BASE_DIR / 'static'),
        static_url_path='/static'
    )
    app.config.from_object(config_class)

    # Initialize Database
    db.init_app(app)

    # Initialize Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access your chat workspace.'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(conversations_bp)

    # Custom Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if app.request_class:
            from flask import request
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Resource not found.'}), 404
        return render_template('base.html', error_code=404, error_message='Page Not Found'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal server error: {error}")
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error occurred.'}), 500
        return render_template('base.html', error_code=500, error_message='Internal Server Error'), 500

    # Initialize database tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables initialized successfully.")
        except Exception as e:
            logger.warning(f"Initial DB connection failed ({e}). Checking fallback to SQLite...")
            if 'mysql' in app.config['SQLALCHEMY_DATABASE_URI']:
                # Fallback to local SQLite if MySQL server is not running
                sqlite_path = app.config['BASE_DIR'] / 'chatbot.db'
                app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{sqlite_path}"
                db.engine.dispose()
                db.create_all()
                logger.info(f"Fallback to SQLite complete: {sqlite_path}")
            else:
                logger.error(f"Failed to initialize database: {e}")

    return app


# Application instance for WSGI/dev server
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    print(f"\n=======================================================")
    print(f"  NovaAI Chatbot Server is starting...")
    print(f"  Running at: http://127.0.0.1:{port}")
    print(f"  AI Mode:    {app.config.get('AI_PROVIDER', 'demo').upper()}")
    print(f"=======================================================\n")
    app.run(host='127.0.0.1', port=port, debug=debug)
